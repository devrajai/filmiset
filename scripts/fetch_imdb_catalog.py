#!/usr/bin/env python3
"""fetch_imdb_catalog.py — ingest IMDb's free public title catalogue (no API key).

IMDb publishes its entire catalogue as plain TSV dumps:
    title.basics.tsv.gz   ~11.6 million rows (movies, shorts, series, episodes, …)
    title.ratings.tsv.gz  average rating + vote count for ~1.5 million of them

This script
  1. downloads both (~190 MB total, free, no signup)
  2. keeps real *titles* (movie / tvMovie / tvSeries / tvMiniSeries / short), drops the
     ~8 million individual tvEpisode rows, and drops adult titles
  3. joins the ratings
  4. writes two small files the repo can hold:
       data/imdb_stats.json -> the true counts per type (so we always know the real size)
       data/imdb_top.json   -> the most-voted slice, in the site's own row shape

Run inside the GitHub Action:

    python3 scripts/fetch_imdb_catalog.py --top 30000
"""
import argparse, csv, gzip, json, os, sys, urllib.request

BASICS = "https://datasets.imdbws.com/title.basics.tsv.gz"
RATINGS = "https://datasets.imdbws.com/title.ratings.tsv.gz"
KEEP = {"movie", "tvMovie", "tvSeries", "tvMiniSeries", "short"}

TYPE_LABEL = {
    "movie": "Movie", "tvMovie": "Movie", "short": "Movie",
    "tvSeries": "Series", "tvMiniSeries": "Series",
}


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
        print(f"  using cached {dest}")
        return dest
    print(f"  downloading {url} …")
    urllib.request.urlretrieve(url, dest)
    return dest


def read_ratings(path):
    out = {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        f.readline()
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                try:
                    out[p[0]] = (float(p[1]), int(p[2]))
                except ValueError:
                    pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30000, help="how many most-voted titles to keep")
    ap.add_argument("--stats", default="data/imdb_stats.json")
    ap.add_argument("--out", default="data/imdb_all.json.gz", help="gzipped when it ends in .gz")
    args = ap.parse_args()

    try:
        ratings = read_ratings(download(RATINGS, "/tmp/imdb_ratings.tsv.gz"))
    except Exception as e:
        print(f"could not fetch IMDb ratings: {type(e).__name__} {e}", file=sys.stderr)
        return
    print(f"  ratings: {len(ratings):,}")

    try:
        basics = download(BASICS, "/tmp/imdb_basics.tsv.gz")
    except Exception as e:
        print(f"could not fetch IMDb basics: {type(e).__name__} {e}", file=sys.stderr)
        return

    total = kept = 0
    per_type, per_year = {}, {}
    rows = []

    with gzip.open(basics, "rt", encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(r, None)
        for p in r:
            if len(p) < 9:
                continue
            total += 1
            ttype = p[1]
            if ttype not in KEEP or p[4] == "1":        # keep real titles, drop adult
                continue
            kept += 1
            per_type[ttype] = per_type.get(ttype, 0) + 1
            year = p[5]
            if year.isdigit():
                per_year[year[:3] + "0s"] = per_year.get(year[:3] + "0s", 0) + 1
            rt = ratings.get(p[0])
            rows.append({
                "id": p[0],
                "t": p[2],
                "y": int(year) if year.isdigit() else "",
                "type": TYPE_LABEL.get(ttype, "Movie"),
                "g": [x for x in (p[8] or "").split(",") if x and x != r"\N"][:3],
                "rt": int(p[7]) if p[7].isdigit() else "",
                "irt": rt[0] if rt else "",
                "ivot": rt[1] if rt else 0,
            })

    print(f"  IMDb rows: {total:,} total, {kept:,} kept as titles")

    stats = {
        "generated_from": "IMDb public datasets (datasets.imdbws.com) — free, no API key",
        "imdb_rows_total": total,
        "titles_kept": kept,
        "by_type": dict(sorted(per_type.items(), key=lambda kv: -kv[1])),
        "rated_titles": sum(1 for r in rows if r["irt"]),
        "by_decade": dict(sorted(per_year.items())),
    }
    os.makedirs(os.path.dirname(args.stats) or ".", exist_ok=True)
    json.dump(stats, open(args.stats, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  wrote {args.stats}")

    rows.sort(key=lambda r: -r["ivot"])
    top = rows[:args.top]
    if args.out.endswith(".gz"):
        with gzip.open(args.out, "wt", encoding="utf-8") as f:
            json.dump(top, f, ensure_ascii=False)
    else:
        json.dump(top, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    mb = os.path.getsize(args.out) / 1048576
    print(f"  wrote {args.out} ({len(top):,} most-voted titles, {mb:.1f} MB)")


if __name__ == "__main__":
    main()
