#!/usr/bin/env python3
"""fetch_boxoffice.py — a hit / flop reading from TMDB's budget and revenue.

    TMDB_API_KEY=xxx python3 scripts/fetch_boxoffice.py --limit 400000 --per-run 200000

Be clear about what this is. TMDB carries budget and revenue for a minority of films, and for
Indian cinema that minority is small. Where both numbers are missing we write nothing at all —
"unknown" is the honest answer, and a guess would be worse than a blank.

Rule: revenue >= 2x budget -> Blockbuster; >= 1.2x -> Hit; < 0.8x -> Flop; otherwise Average.
"""
import argparse, json, os, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api.themoviedb.org/3"
OUT = "data/boxoffice.json"


def fetch(tmdb_id, key):
    url = f"{API}/movie/{tmdb_id}?api_key={key}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d.get("budget") or 0, d.get("revenue") or 0


def verdict(budget, revenue):
    if budget <= 0 or revenue <= 0:
        return None
    ratio = revenue / budget
    if ratio >= 2:   return "Blockbuster"
    if ratio >= 1.2: return "Hit"
    if ratio < 0.8:  return "Flop"
    return "Average"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=400000)
    ap.add_argument("--per-run", type=int, default=200000)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--tmdb-ids", default="data/tmdb_ids.json",
                    help="map of imdb id -> tmdb id, produced by fetch_tmdb_exports.py")
    args = ap.parse_args()
    key = (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDBKEY") or "").strip()
    if not key:
        print("TMDB_API_KEY not set — skipping box office."); return

    known = {}
    if os.path.exists(OUT):
        try: known = json.load(open(OUT, encoding="utf-8"))
        except Exception: known = {}
    ids = {}
    if os.path.exists(args.tmdb_ids):
        try: ids = json.load(open(args.tmdb_ids, encoding="utf-8"))
        except Exception: ids = {}
    todo = [(imdb, tm) for imdb, tm in list(ids.items())[: args.limit] if imdb not in known][: args.per_run]
    print(f"already known: {len(known):,} | asking TMDB about {len(todo):,}")
    if not todo:
        return

    def work(pair):
        imdb, tm = pair
        try:
            b, r = fetch(tm, key)
            v = verdict(b, r)
            return imdb, ({"budget": b, "revenue": r, "verdict": v} if v else None)
        except Exception:
            return imdb, None

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for imdb, rec in ex.map(work, todo):
            if rec: known[imdb] = rec
            done += 1
            if done % 20000 == 0:
                print(f"  {done:,} checked, {len(known):,} with figures", flush=True)
                json.dump(known, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(known, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    from collections import Counter
    print(f"wrote {OUT}: {len(known):,} titles with a budget/revenue pair")
    print("  verdicts:", dict(Counter(v["verdict"] for v in known.values())))


if __name__ == "__main__":
    main()
