#!/usr/bin/env python3
"""fetch_tmdb_details.py — rolling cast / director / overview fetcher (needs TMDB_API_KEY).

The IMDb sheet shards carry title, year, genre, rating and votes, but no cast, director or
synopsis. This fills that gap for the most-voted titles, in popularity order, and stores the
result in the repo so the site never needs TMDB at runtime.

    data/imdb_details.json.gz   { "tt0111161": {"d": "Frank Darabont",
                                                "c": ["Tim Robbins", "Morgan Freeman"],
                                                "o": "Over the hill and far away…"} }

Rolling and resumable: each run covers the next --per-run titles that have no entry yet.
Once the catalogue is complete the TMDB steps (and the key) can simply be switched off —
nothing the site loads comes from TMDB.

    TMDB_API_KEY=xxxx python3 scripts/fetch_tmdb_details.py --limit 300000 --per-run 20000
"""
import argparse, gzip, json, os, sys, threading, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

TMDB = "https://api.themoviedb.org/3"
OUT = "data/imdb_details.json.gz"
SRC = "data/imdb_all.json.gz"

_lock = threading.Lock()


def tmdb(path, key, params=None, tries=3):
    q = dict(params or {})
    q["api_key"] = key
    url = f"{TMDB}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.5 * (a + 1))
                continue
            return None
        except Exception:
            time.sleep(0.4 * (a + 1))
    return None


def details_for(tconst, key):
    d = tmdb(f"/find/{tconst}", key, {"external_source": "imdb_id"})
    if not d:
        return None
    for bucket, kind in (("movie_results", "movie"), ("tv_results", "tv")):
        hits = d.get(bucket) or []
        if not hits:
            continue
        tid = hits[0].get("id")
        if not tid:
            continue
        full = tmdb(f"/{kind}/{tid}", key, {"append_to_response": "credits"})
        if not full:
            continue
        crew = ((full.get("credits") or {}).get("crew")) or []
        cast = ((full.get("credits") or {}).get("cast")) or []
        directors = [c.get("name") for c in crew if c.get("job") == "Director" and c.get("name")]
        if not directors:
            creators = full.get("created_by") or []
            directors = [c.get("name") for c in creators if c.get("name")]
        out = {}
        if directors:
            out["d"] = ", ".join(directors[:2])
        if cast:
            out["c"] = [c.get("name") for c in cast[:5] if c.get("name")]
        ov = (full.get("overview") or "").strip()
        if ov:
            out["o"] = ov[:600]
        if full.get("runtime") and kind == "movie":
            out["r"] = full["runtime"]
        return out or None
    return None


def load_source(limit):
    rows = []
    try:
        import ijson
        with gzip.open(SRC, "rt", encoding="utf-8") as f:
            for i, item in enumerate(ijson.items(f, "item")):
                if i >= limit:
                    break
                rows.append(item)
    except Exception as e:
        print(f"could not read {SRC}: {type(e).__name__} {e}", file=sys.stderr)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300000)
    ap.add_argument("--per-run", type=int, default=20000)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    key = (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDBKEY") or "").strip()
    if not key:
        print("TMDB_API_KEY not set — skipping details (site keeps working).")
        return

    known = {}
    if os.path.exists(OUT):
        try:
            with gzip.open(OUT, "rt", encoding="utf-8") as f:
                known = json.load(f)
        except Exception:
            known = {}
    print(f"already have details for {len(known):,} titles")

    rows = load_source(args.limit)
    todo = [r.get("id") for r in rows if r.get("id") and r["id"] not in known]
    if args.per_run:
        todo = todo[:args.per_run]
    print(f"to fetch this run: {len(todo):,} with {args.workers} workers")

    done = [0]
    hits = [0]
    t0 = time.time()

    def work(tconst):
        res = details_for(tconst, key)
        with _lock:
            known[tconst] = res or {}
            done[0] += 1
            if res:
                hits[0] += 1
            if done[0] % 2000 == 0:
                rate = done[0] / max(time.time() - t0, 1)
                print(f"  {done[0]:,}/{len(todo):,} ({hits[0]:,} enriched, {rate:.0f}/s)")
                with gzip.open(OUT, "wt", encoding="utf-8") as f:
                    json.dump(known, f, ensure_ascii=False)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, todo))

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump(known, f, ensure_ascii=False)
    enriched = sum(1 for v in known.values() if v)
    print(f"wrote {OUT}: {len(known):,} looked up, {enriched:,} enriched ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
