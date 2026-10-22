#!/usr/bin/env python3
"""fetch_posters_tmdb.py — rolling poster fetcher for the IMDb rows (needs TMDB_API_KEY).

The IMDb dataset has no images, so the 2.4M titles in the sheet shards have no poster.
This script looks posters up on TMDB by IMDb id and keeps a small map the site can use:

    data/imdb_posters.json   { "tt0111161": "https://image.tmdb.org/t/p/w300/xxx.jpg", ... }

It is *rolling*: each run fetches posters for the next N most-voted titles that do not
have one yet, so coverage grows a little every day without hammering the API.

The poster URLs are public (image.tmdb.org needs no key to view), so they keep working
even after the TMDB API key is disconnected.

    TMDB_API_KEY=xxxx python3 scripts/fetch_posters_tmdb.py --limit 10000
"""
import argparse, gzip, json, os, sys, time, urllib.parse, urllib.request

TMDB = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w300"
MAP = "data/imdb_posters.json"
SRC = "data/imdb_all.json.gz"


def tmdb(path, key, params=None):
    q = dict(params or {})
    q["api_key"] = key
    url = f"{TMDB}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def poster_for(tconst, key):
    try:
        d = tmdb(f"/find/{tconst}", key, {"external_source": "imdb_id"})
        for bucket in ("movie_results", "tv_results"):
            for hit in d.get(bucket, []) or []:
                if hit.get("poster_path"):
                    return IMG + hit["poster_path"]
    except Exception:
        pass
    return ""


def load_source(limit):
    """The N most-voted titles (the file is already sorted by votes)."""
    out = []
    try:
        with gzip.open(SRC, "rt", encoding="utf-8") as f:
            import ijson
            for i, item in enumerate(ijson.items(f, "item")):
                if i >= limit:
                    break
                out.append(item)
    except Exception as e:
        print(f"could not read {SRC}: {type(e).__name__} {e}", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10000, help="how many titles to cover in total (most-voted first)")
    ap.add_argument("--per-run", type=int, default=0, help="max new posters this run (0 = fill the whole limit)")
    ap.add_argument("--delay", type=float, default=0.08)
    args = ap.parse_args()

    key = (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDBKEY") or "").strip()
    if not key:
        print("TMDB_API_KEY not set — skipping posters (site keeps working).")
        return

    poster_map = {}
    if os.path.exists(MAP):
        try:
            poster_map = json.load(open(MAP, encoding="utf-8"))
        except Exception:
            poster_map = {}
    print(f"already have {len(poster_map):,} posters")

    rows = load_source(args.limit)
    if not rows:
        print("no source rows — nothing to do.")
        return
    print(f"looking at the top {len(rows):,} titles")

    todo = [r.get("id") for r in rows if r.get("id") and r["id"] not in poster_map]
    if args.per_run:
        todo = todo[:args.per_run]
    print(f"to fetch this run: {len(todo):,}")

    hit = 0
    for n, tconst in enumerate(todo, 1):
        url = poster_for(tconst, key)
        poster_map[tconst] = url
        if url:
            hit += 1
        if n % 500 == 0:
            print(f"  {n:,}/{len(todo):,}  ({hit:,} with a poster)")
        time.sleep(args.delay)

    os.makedirs(os.path.dirname(MAP) or ".", exist_ok=True)
    json.dump(poster_map, open(MAP, "w", encoding="utf-8"), ensure_ascii=False)
    with_poster = sum(1 for v in poster_map.values() if v)
    print(f"wrote {MAP}: {len(poster_map):,} looked up, {with_poster:,} have a poster")


if __name__ == "__main__":
    main()
