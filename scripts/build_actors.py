#!/usr/bin/env python3
"""build_actors.py — who is in what, and what else they were in.

Two things the catalogue cannot answer on its own: clicking an actor's name to see their films, and
opening a film to see who is in it. Both come from two IMDb files:

  title.principals.tsv.gz   tconst, nconst, category, characters   — who was in which title
  name.basics.tsv.gz        nconst, primaryName, birthYear, ...    — who they are

The output is bucketed by the last two digits of the id, the same trick the title catalogue and the
episode packs already use, so a page fetches one file of a few hundred KB rather than a hundred MB:

  data/act/act_<XX>.json.gz    {nconst: [name, birthYear, [[titleId, title, year, rating, votes], ...]]}
  data/act/cast_<XX>.json.gz   {titleId: [[nconst, name, role], ...]}

Only actors with at least --min-films titles in the catalogue are kept, so the files stay close to
the number of people someone might actually look up.

    python3 build_actors.py --principals title.principals.tsv.gz --names name.basics.tsv.gz \\
        --catalogue data --ratings title.ratings.tsv.gz --basics title.basics.tsv.gz --out data/act
"""
import argparse, csv, glob, gzip, io, json, os, sys, time
from collections import defaultdict

def open_maybe_gz(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", newline="")
    return open(path, encoding="utf-8", newline="")

def norm_id(t):
    t = (t or "").strip()
    if t[:2] in ("tt", "nm") and t[2:].isdigit():
        t = t[2:]
    return str(int(t)) if t.isdigit() else t

def bucket(key):
    return ("%02d" % (int(key) % 100)) if str(key).isdigit() else "xx"

def catalogue(data_dir):
    """id -> (title, year, rating, votes), for everything the site already ships."""
    out = {}
    for p in glob.glob(os.path.join(data_dir, "ix_*.json.gz")):
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        n = len(d.get("t", []))
        for i in range(n):
            out[str(d["i"][i])] = (d["t"][i], d["y"][i], d["r"][i], d["v"][i])
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--principals", default="title.principals.tsv.gz")
    ap.add_argument("--names", default="name.basics.tsv.gz")
    ap.add_argument("--catalogue", default="data")
    ap.add_argument("--out", default="data/act")
    ap.add_argument("--min-films", type=int, default=2)
    a = ap.parse_args()

    for f in (a.principals, a.names):
        if not os.path.exists(f):
            print(f"missing {f}"); sys.exit(1)

    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    print("reading the catalogue…")
    cat = catalogue(a.catalogue)
    if not cat:
        print("no catalogue ids — run the packer first"); sys.exit(1)
    print(f"  {len(cat):,} titles")

    # ---- 1. who was in what, for titles we ship ----
    print("reading title.principals…")
    cast = defaultdict(list)          # titleId -> [(nconst, role)]
    people = defaultdict(list)        # nconst -> [titleId]
    rows = 0
    with open_maybe_gz(a.principals) as f:
        r = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in r:
            tid = norm_id(row.get("tconst"))
            if tid not in cat:
                continue
            nid = norm_id(row.get("nconst"))
            if not nid:
                continue
            role = (row.get("characters") or row.get("category") or "").strip().strip('"')
            if len(role) > 60: role = role[:57] + "…"
            cast[tid].append((nid, role))
            people[nid].append(tid)
            rows += 1
    print(f"  {rows:,} credits across {len(cast):,} titles, {len(people):,} people")

    # keep only people with enough titles to be worth a page
    keep = {nid for nid, tids in people.items() if len(set(tids)) >= a.min_films}
    print(f"  {len(keep):,} people with {a.min_films}+ titles")

    # ---- 2. who they are ----
    print("reading name.basics…")
    names = {}
    with open_maybe_gz(a.names) as f:
        r = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in r:
            nid = norm_id(row.get("nconst"))
            if nid not in keep:
                continue
            by = row.get("birthYear") or ""
            names[nid] = (row.get("primaryName") or "", int(by) if by.isdigit() else 0)
    print(f"  {len(names):,} named")

    # ---- 3. write the actor buckets ----
    print("writing actor buckets…")
    by_bucket = defaultdict(dict)
    for nid in keep:
        if nid not in names: continue
        nm, by = names[nid]
        films = []
        for tid in dict.fromkeys(people[nid]):          # dedupe, keep order
            t, y, r, v = cat[tid]
            films.append([tid, t, y, r, v])
        films.sort(key=lambda x: -(x[4] or 0))          # most watched first
        by_bucket[bucket(nid)][nid] = [nm, by, films]

    total_a = 0
    for b, obj in sorted(by_bucket.items()):
        p = os.path.join(a.out, f"act_{b}.json.gz")
        with gzip.open(p, "wt", encoding="utf-8", compresslevel=9) as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        total_a += os.path.getsize(p)

    # ---- 4. write the cast buckets ----
    print("writing cast buckets…")
    by_bucket_c = defaultdict(dict)
    for tid, credits in cast.items():
        out = []
        for nid, role in credits[:20]:                  # a card does not need the whole crew
            nm = names.get(nid, ("", 0))[0]
            if nm: out.append([nid, nm, role])
        if out: by_bucket_c[bucket(tid)][tid] = out

    total_c = 0
    for b, obj in sorted(by_bucket_c.items()):
        p = os.path.join(a.out, f"cast_{b}.json.gz")
        with gzip.open(p, "wt", encoding="utf-8", compresslevel=9) as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        total_c += os.path.getsize(p)

    man = {"people": sum(len(v) for v in by_bucket.values()),
           "titles_with_cast": sum(len(v) for v in by_bucket_c.values()),
           "actor_files": len(by_bucket), "cast_files": len(by_bucket_c),
           "actor_bytes": total_a, "cast_bytes": total_c,
           "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(man, open(os.path.join(a.out, "_manifest.json"), "w"), separators=(",", ":"))

    print(f"\nactor files: {len(by_bucket)}  ({total_a/1024**2:.1f} MB)")
    print(f"cast files : {len(by_bucket_c)}  ({total_c/1024**2:.1f} MB)")
    print(f"people     : {man['people']:,}")
    print(f"took {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
