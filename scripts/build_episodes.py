#!/usr/bin/env python3
"""build_episodes.py — attach every episode to its series, straight from IMDb's own files.

The master database has about 4.5 million episode rows but no parent link: no series id, no season
number, no episode number. Without those an episode is a title with nothing to hang from, which is
why the site could not show them. The link exists in IMDb's title.episode dataset, and the titles,
years and ratings are in the two files the workflow already downloads.

So this does not need the master database at all. It joins three IMDb files:

  title.episode.tsv.gz   tconst, parentTconst, seasonNumber, episodeNumber
  title.basics.tsv.gz    tconst, titleType, primaryTitle, startYear, runtimeMinutes, genres
  title.ratings.tsv.gz   tconst, averageRating, numVotes

and writes one small gzipped file per series, keyed by the series' IMDb id, so the site fetches a
single file when someone opens a show:

  data/ep/<seriesId>.json.gz   {"n": 5, "e": [[season, episode, title, year, rating, votes], ...]}

Only series that the catalogue actually contains are kept, so the output stays close to the number
of shows rather than the number of episodes.

    python3 build_episodes.py --basics title.basics.tsv.gz --ratings title.ratings.tsv.gz \\
        --episodes title.episode.tsv.gz --catalogue data --out data/ep
"""
import argparse, csv, glob, gzip, io, json, os, sys, time

def open_maybe_gz(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", newline="")
    return open(path, encoding="utf-8", newline="")

def norm_id(t):
    """tt0000001 -> 0000001, the same shape the packed buckets use."""
    t = (t or "").strip()
    if t.startswith("tt") and t[2:].isdigit():
        t = t[2:]
    return str(int(t)) if t.isdigit() else t

def catalogue_ids(data_dir):
    """Every id the site already ships, so we only build episodes for shows we can show."""
    ids = set()
    for p in glob.glob(os.path.join(data_dir, "ix_*.json.gz")):
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                d = json.load(f)
            for v in d.get("i", []):
                ids.add(str(v))
        except Exception:
            continue
    print(f"  catalogue ids: {len(ids):,}")
    return ids

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basics", default="title.basics.tsv.gz")
    ap.add_argument("--ratings", default="title.ratings.tsv.gz")
    ap.add_argument("--episodes", default="title.episode.tsv.gz")
    ap.add_argument("--catalogue", default="data")
    ap.add_argument("--out", default="data/ep")
    ap.add_argument("--min-votes", type=int, default=0)
    a = ap.parse_args()

    for f in (a.basics, a.ratings, a.episodes):
        if not os.path.exists(f):
            print(f"missing {f} — the workflow downloads these before this step"); sys.exit(1)

    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    # ---- 1. which series do we ship? ----
    print("reading the catalogue…")
    ship = catalogue_ids(a.catalogue)
    if not ship:
        print("no catalogue ids found — run the packer first"); sys.exit(1)

    # ---- 2. episode -> series, with season and episode numbers ----
    print("reading title.episode…")
    parent = {}                     # episode id -> (parent, season, episode)
    want_parents = set()
    n = 0
    with open_maybe_gz(a.episodes) as f:
        r = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in r:
            pid = norm_id(row.get("parentTconst"))
            if pid not in ship:     # a show we do not carry: skip it entirely
                continue
            eid = norm_id(row.get("tconst"))
            try:
                s = int(row.get("seasonNumber") or 0)
                e = int(row.get("episodeNumber") or 0)
            except ValueError:
                s = e = 0
            parent[eid] = (pid, s, e)
            want_parents.add(pid)
            n += 1
    print(f"  {n:,} episodes across {len(want_parents):,} series")
    if not n:
        print("no episodes matched — are the catalogue ids in the same shape?"); sys.exit(1)

    # ---- 3. titles, years and runtime for those episodes ----
    print("reading title.basics…")
    meta = {}
    m = 0
    with open_maybe_gz(a.basics) as f:
        r = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in r:
            tid = norm_id(row.get("tconst"))
            if tid not in parent:
                continue
            meta[tid] = (
                row.get("primaryTitle") or "",
                int(row.get("startYear")) if (row.get("startYear") or "").isdigit() else 0,
                int(row.get("runtimeMinutes")) if (row.get("runtimeMinutes") or "").isdigit() else 0,
            )
            m += 1
    print(f"  {m:,} episode titles found")

    # ---- 4. ratings ----
    print("reading title.ratings…")
    rate = {}
    with open_maybe_gz(a.ratings) as f:
        r = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in r:
            tid = norm_id(row.get("tconst"))
            if tid in parent:
                try:
                    rate[tid] = (round(float(row["averageRating"]) * 10),
                                 int(row["numVotes"]))
                except (KeyError, ValueError, TypeError):
                    pass
    print(f"  {len(rate):,} rated")

    # ---- 5. group by series and write ----
    print("writing packs…")
    by_series = {}
    for eid, (pid, s, e) in parent.items():
        t, y, rt = meta.get(eid, ("", 0, 0))
        rv = rate.get(eid, (0, 0))
        if rv[1] < a.min_votes:
            continue
        by_series.setdefault(pid, []).append([s, e, t, y, rt, rv[0], rv[1]])

    total = 0
    written = 0
    for pid, eps in by_series.items():
        eps.sort(key=lambda x: (x[0], x[1]))
        obj = {"n": len(eps), "e": eps}
        p = os.path.join(a.out, f"{pid}.json.gz")
        with gzip.open(p, "wt", encoding="utf-8", compresslevel=9) as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        total += os.path.getsize(p)
        written += 1

    # a small manifest so the site knows which series have episodes without probing each one
    man = {"series": written, "episodes": sum(len(v) for v in by_series.values()),
           "bytes": total, "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(man, open(os.path.join(a.out, "_manifest.json"), "w"), separators=(",", ":"))

    print(f"\nwrote {written:,} series files, {total/1024**2:.1f} MB in {time.time()-t0:.0f}s")
    print(f"  episodes: {man['episodes']:,}")
    print(f"  average : {man['episodes']/max(1,written):.1f} per series")
    print(f"  biggest : {max((os.path.getsize(os.path.join(a.out,f)) for f in os.listdir(a.out) if f.endswith('.gz')), default=0)/1024:.0f} KB")

if __name__ == "__main__":
    main()
