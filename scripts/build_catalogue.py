#!/usr/bin/env python3
"""build_catalogue.py — rebuild the ix buckets from IMDb's own files.

The site's search index is fourteen gzipped files, one per group of first letters, each holding
parallel arrays of id, title, year, rating and votes. Nothing in the repo produced them any more —
they had been built once and then hosted — so when a bad deployment deleted them from Cloudflare
there was no way back. This is that way back.

    python3 build_catalogue.py --data data --out data

Reads  title.basics.tsv.gz and title.ratings.tsv.gz, writes ix_<group>.json.gz plus ix_manifest.json.

Bucketing matches the site exactly: the title is lowercased, a leading article is stripped, and the
first remaining letter picks the file. "The Golden Spoon" files under GO, not TH — the first build
got that wrong and search could not find it.
"""
import argparse, gzip, json, os, re, sys, time
from collections import defaultdict

# the groups the site asks for, in order
GROUPS = ["ab", "cd", "ef", "gh", "ij", "kl", "mn", "num", "op", "qr", "st", "uv", "wx", "yz"]
ARTICLES = ("the ", "a ", "an ", "el ", "la ", "le ", "les ", "der ", "die ", "das ")


def norm(title):
    """The same normalisation the site uses before it decides which file to fetch."""
    t = str(title or "").lower()
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    t = " ".join(t.split())
    for a in ARTICLES:
        if t.startswith(a) and len(t) > len(a):
            t = t[len(a):]
            break
    return t


def group_of(title):
    n = norm(title)
    if not n:
        return None
    c = n[0]
    if c.isdigit():
        return "num"
    if not c.isalpha():
        return None
    for g in GROUPS:
        if g != "num" and c in g:
            return g
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data", help="where the IMDb tsv.gz files are")
    ap.add_argument("--out", default="data", help="where to write the buckets")
    ap.add_argument("--min-votes", type=int, default=0)
    a = ap.parse_args()

    basics = os.path.join(a.data, "title.basics.tsv.gz")
    ratings = os.path.join(a.data, "title.ratings.tsv.gz")
    for p in (basics, ratings):
        if not os.path.exists(p):
            print(f"missing {p}"); sys.exit(1)

    t0 = time.time()

    # ---- ratings first: id -> (rating*10, votes) ----
    print("reading ratings…")
    rat = {}
    with gzip.open(ratings, "rt", encoding="utf-8", errors="replace") as f:
        next(f, None)
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 3:
                continue
            tid, avg, votes = p[0], p[1], p[2]
            if tid == "tconst":
                continue
            try:
                r = int(round(float(avg) * 10))
                v = int(votes)
            except ValueError:
                continue
            rat[tid] = (r, v)
    print(f"  {len(rat):,} rated titles")

    # ---- basics: keep the types the site shows ----
    KEEP = {"movie", "tvSeries", "tvMiniSeries", "tvMovie", "short", "tvShort", "tvSpecial"}
    buckets = defaultdict(lambda: {"i": [], "t": [], "y": [], "r": [], "v": []})
    seen = 0
    kept = 0

    print("reading titles…")
    with gzip.open(basics, "rt", encoding="utf-8", errors="replace") as f:
        header = next(f, None)
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 9:
                continue
            tid, ttype, primary, original, adult, year, endy, runtime, genres = p[:9]
            if ttype not in KEEP or adult == "1":
                continue
            title = primary if primary != "\\N" else original
            if not title or title == "\\N":
                continue
            seen += 1
            rv = rat.get(tid)
            if not rv:
                continue
            r, v = rv
            if v < a.min_votes:
                continue
            g = group_of(title)
            if not g:
                continue
            y = year if year.isdigit() else ""
            b = buckets[g]
            # strip the tt prefix — the site re-adds it
            b["i"].append(int(tid[2:]) if tid[2:].isdigit() else tid)
            b["t"].append(title)
            b["y"].append(int(y) if y else 0)
            b["r"].append(r)
            b["v"].append(v)
            kept += 1
            if kept % 200000 == 0:
                print(f"  {kept:,} kept…", flush=True)

    print(f"  {seen:,} candidate titles, {kept:,} with a rating")

    os.makedirs(a.out, exist_ok=True)
    total_bytes = 0
    manifest = {}
    for g in GROUPS:
        b = buckets.get(g)
        if not b:
            print(f"  {g}: empty"); continue
        # sort by votes so the best-known title comes first, which is what the site ranks on
        order = sorted(range(len(b["v"])), key=lambda k: -b["v"][k])
        obj = {k: [b[k][j] for j in order] for k in ("i", "t", "y", "r", "v")}
        path = os.path.join(a.out, f"ix_{g}.json.gz")
        with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        size = os.path.getsize(path)
        total_bytes += size
        manifest[g] = {"n": len(obj["i"]), "bytes": size}
        print(f"  {g:4s} {len(obj['i']):>8,} titles  {size/1024:>7.1f} KB")

    man = {"titles": kept, "groups": manifest, "bytes": total_bytes,
           "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(os.path.join(a.out, "ix_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, separators=(",", ":"))

    print(f"\ntotal {kept:,} titles in {len(manifest)} buckets, {total_bytes/1024**2:.1f} MB")
    print(f"took {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
