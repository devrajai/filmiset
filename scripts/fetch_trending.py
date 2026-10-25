#!/usr/bin/env python3
"""fetch_trending.py — what is trending right now (TMDB), for the "Trending now" chip.

    TMDB_API_KEY=xxx python3 scripts/fetch_trending.py

Writes data/trending.json as a plain list of titles, so the site never calls TMDB itself.
"""
import argparse, json, os, time, urllib.parse, urllib.request
import sys

TMDB = "https://api.themoviedb.org/3"
OUT = "data/trending.json"


def get(path, key, params=None):
    q = dict(params or {}); q["api_key"] = key
    req = urllib.request.Request(f"{TMDB}{path}?{urllib.parse.urlencode(q)}",
                                 headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))



def _verify_key(key):
    """Prove the key works before doing thousands of lookups. A key that is present but rejected
    looks exactly like a key that is missing, and that is how this step stayed broken for days:
    the run reported success while producing nothing."""
    try:
        req = urllib.request.Request(f"{TMDB}/configuration?api_key={key}",
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            json.loads(r.read().decode("utf-8"))
        print("TMDB key verified \u2713")
        return True
    except Exception as e:
        print(f"::error::TMDB_API_KEY is present but the call failed: {type(e).__name__} {str(e)[:120]}")
        return False

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--region", default="IN"); args = ap.parse_args()
    key = (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDBKEY") or "").strip()
    if not _verify_key(key):
        sys.exit(1)
    if not key:
        print("TMDB_API_KEY not set — skipping trending (site keeps working)."); return
    titles, seen = [], set()
    for window in ("day", "week"):
        for i in (1, 2):                                   # two pages each
            try:
                d = get(f"/trending/all/{window}", key, {"page": i})
            except Exception as e:
                print(f"  {window} p{i}: {type(e).__name__}"); continue
            for it in d.get("results") or []:
                t = it.get("title") or it.get("name") or ""
                if t and t.lower() not in seen:
                    seen.add(t.lower()); titles.append(t)
            time.sleep(0.2)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    json.dump(titles, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {OUT}: {len(titles)} trending titles")


if __name__ == "__main__":
    main()
