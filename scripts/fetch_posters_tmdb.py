#!/usr/bin/env python3
"""fetch_posters_tmdb.py — rolling poster fetcher for the IMDb rows (needs TMDB_API_KEY).

The IMDb dataset has no images, so the 2.4M titles in the sheet shards have no poster.
This script looks posters up on TMDB by IMDb id and keeps a small map the site can use:

    data/imdb_posters.json   { "tt0111161": "https://image.tmdb.org/t/p/w300/xxx.jpg", ... }

It is *rolling*: each run fetches posters for the next N most-voted titles that do not have one
yet, so coverage grows every day without hammering the API.

Requests run through a thread pool (TMDB allows roughly 50 requests/second), so a run covers
tens of thousands of titles in minutes rather than hours. 429s are retried with a backoff.

    TMDB_API_KEY=xxxx python3 scripts/fetch_posters_tmdb.py --limit 500000 --per-run 50000
"""
import argparse, gzip, json, os, sys, threading, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

TMDB = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w300"
MAP = "data/imdb_posters.json"
SRC = "data/imdb_all.json.gz"

_lock = threading.Lock()


def tmdb(path, key, params=None, tries=3):
    q = dict(params or {})
    q["api_key"] = key
    url = f"{TMDB}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:                      # rate limited — back off and retry
                time.sleep(1.5 * (attempt + 1))
                continue
            return None
        except Exception:
            time.sleep(0.4 * (attempt + 1))
    return None


def poster_for(tconst, key):
    d = tmdb(f"/find/{tconst}", key, {"external_source": "imdb_id"})
    if not d:
        return ""
    for bucket in ("movie_results", "tv_results"):
        for hit in d.get(bucket, []) or []:
            if hit.get("poster_path"):
                return IMG + hit["poster_path"]
    return ""


def load_source(limit):
    """The N most-voted titles (the file is already sorted by votes)."""
    out = []
    try:
        import ijson
        with gzip.open(SRC, "rt", encoding="utf-8") as f:
            for i, item in enumerate(ijson.items(f, "item")):
                if i >= limit:
                    break
                out.append(item)
    except Exception as e:
        print(f"could not read {SRC}: {type(e).__name__} {e}", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=500000,
                    help="how many titles to cover in total (most-voted first)")
    ap.add_argument("--per-run", type=int, default=0, help="max new posters this run (0 = fill the whole limit)")
    ap.add_argument("--workers", type=int, default=12, help="parallel requests")
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
    print(f"to fetch this run: {len(todo):,} with {args.workers} workers")

    done = [0]
    hits = [0]
    t0 = time.time()

    def work(tconst):
        url = poster_for(tconst, key)
        with _lock:
            poster_map[tconst] = url
            done[0] += 1
            if url:
                hits[0] += 1
            if done[0] % 5000 == 0:
                rate = done[0] / max(time.time() - t0, 1)
                print(f"  {done[0]:,}/{len(todo):,}  ({hits[0]:,} with a poster, {rate:.0f}/s)")
                json.dump(poster_map, open(MAP, "w", encoding="utf-8"), ensure_ascii=False)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, todo))

    os.makedirs(os.path.dirname(MAP) or ".", exist_ok=True)
    json.dump(poster_map, open(MAP, "w", encoding="utf-8"), ensure_ascii=False)
    with_poster = sum(1 for v in poster_map.values() if v)
    print(f"wrote {MAP}: {len(poster_map):,} looked up, {with_poster:,} have a poster "
          f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
