#!/usr/bin/env python3
"""fetch_imdb_indian.py — surface the Indian titles hiding inside the IMDb dataset.

Why this exists: IMDb's main dump stores only the *original* title, so a Hindi/Tamil/Telugu
show sits in the catalogue under a name nobody searches for, and — with far fewer votes than
the Hollywood blockbusters — it never reaches the top of the vote-sorted sheets.

IMDb also publishes `title.akas.tsv.gz`, which lists every regional / alternate title with its
**region** and **language**. This script uses it to tag the Indian titles, joins them with the
ratings, and keeps the most-voted ones in the site's own row shape.

Free, no API key. Writes data/imdb_indian.json.

    python3 scripts/fetch_imdb_indian.py --top 20000
"""
import argparse, csv, gzip, json, os, sys, urllib.request

AKAS = "https://datasets.imdbws.com/title.akas.tsv.gz"
BASICS = "https://datasets.imdbws.com/title.basics.tsv.gz"
RATINGS = "https://datasets.imdbws.com/title.ratings.tsv.gz"

# regions / languages that mean "Indian"
INDIAN_LANGS = {"hi", "ta", "te", "ml", "kn", "gu", "mr", "bn", "pa", "as", "or", "ur", "ne", "sa"}
KEEP_TYPES = {"movie", "tvMovie", "tvSeries", "tvMiniSeries", "short"}
TYPE_LABEL = {"movie": "Movie", "tvMovie": "Movie", "short": "Movie",
              "tvSeries": "Series", "tvMiniSeries": "Series"}


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
        print(f"  using cached {dest}")
        return dest
    print(f"  downloading {url} …")
    urllib.request.urlretrieve(url, dest)
    return dest


def indian_ids(akas_path):
    """tconsts that have an Indian region or language."""
    ids = set()
    with gzip.open(akas_path, "rt", encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(r, None)
        for p in r:
            if len(p) < 8:
                continue
            region, lang = p[3], p[4]
            if region == "IN" or lang in INDIAN_LANGS:
                ids.add(p[0])
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=20000, help="how many most-voted Indian titles to keep")
    ap.add_argument("--out", default="data/imdb_indian.json")
    args = ap.parse_args()

    try:
        ratings = {}
        with gzip.open(download(RATINGS, "/tmp/imdb_ratings.tsv.gz"), "rt", encoding="utf-8") as f:
            f.readline()
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 3:
                    try:
                        ratings[p[0]] = (float(p[1]), int(p[2]))
                    except ValueError:
                        pass
        print(f"  ratings: {len(ratings):,}")

        ids = indian_ids(download(AKAS, "/tmp/imdb_akas.tsv.gz"))
        print(f"  Indian titles found in akas: {len(ids):,}")
        if not ids:
            return
    except Exception as e:
        print(f"could not prepare the Indian set: {type(e).__name__} {e}", file=sys.stderr)
        return

    rows = []
    try:
        with gzip.open(download(BASICS, "/tmp/imdb_basics.tsv.gz"), "rt", encoding="utf-8", newline="") as f:
            r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
            next(r, None)
            for p in r:
                if len(p) < 9 or p[0] not in ids:
                    continue
                if p[1] not in KEEP_TYPES or p[4] == "1":
                    continue
                rt = ratings.get(p[0])
                date = p[5] if p[5].isdigit() else ""
                rows.append({
                    "id": p[0],
                    "t": p[2],
                    "y": int(date) if date else "",
                    "type": TYPE_LABEL.get(p[1], "Movie"),
                    "g": [x for x in (p[8] or "").split(",") if x and x != r"\N"][:3],
                    "rt": int(p[7]) if p[7].isdigit() else "",
                    "irt": rt[0] if rt else "",
                    "ivot": rt[1] if rt else 0,
                })
    except Exception as e:
        print(f"could not read basics: {type(e).__name__} {e}", file=sys.stderr)
        return

    print(f"  Indian titles with metadata: {len(rows):,}")
    rows.sort(key=lambda r: -r["ivot"])
    top = rows[:args.top]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    json.dump(top, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  wrote {args.out}: {len(top):,} Indian titles (top {len(top)} by votes)")


if __name__ == "__main__":
    main()
