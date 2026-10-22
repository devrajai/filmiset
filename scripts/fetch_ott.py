#!/usr/bin/env python3
"""fetch_ott.py — fill OTT availability ("which platform is this on?") using TMDB.

Two stages:
  1. Re-apply everything already known from data/ott_cache.json  (no key needed).
     This is important because fetch_data.py regenerates the catalogue and resets `o`.
  2. Look up the remaining titles on TMDB (needs a free key in TMDB_API_KEY).

If no key is present, stage 1 still runs and the script exits 0 — the site keeps working.

    TMDB_API_KEY=xxxxxxxx python3 scripts/fetch_ott.py --region IN
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

TMDB = "https://api.themoviedb.org/3"
CACHE = "data/ott_cache.json"

PROVIDER_MAP = {
    "netflix": "Netflix", "amazon prime video": "Prime Video", "amazon video": "Prime Video",
    "prime video": "Prime Video", "jiohotstar": "JioHotstar", "disney+ hotstar": "JioHotstar",
    "hotstar": "JioHotstar", "jiocinema": "JioCinema", "zee5": "ZEE5", "sonyliv": "SonyLIV",
    "sony liv": "SonyLIV", "hbo max": "HBO Max", "jiohbo": "HBO Max", "apple tv+": "Apple TV+",
    "apple tv plus": "Apple TV+", "crunchyroll": "Crunchyroll", "mx player": "MX Player",
    "youtube": "YouTube", "aha": "Aha", "sun nxt": "Sun NXT", "hoichoi": "Hoichoi",
    "lionsgate play": "Lionsgate Play", "discovery+": "Discovery+", "discovery plus": "Discovery+",
}


def canon(name):
    return PROVIDER_MAP.get((name or "").strip().lower())


def tmdb(path, key, params=None):
    q = dict(params or {})
    q["api_key"] = key
    url = f"{TMDB}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def providers_for(title, year, key, region):
    try:
        params = {"query": title, "include_adult": "false"}
        if year:
            params["year"] = str(year)
        res = tmdb("/search/movie", key, params).get("results", [])
        if not res:
            res = tmdb("/search/movie", key, {"query": title}).get("results", [])
        if not res:
            return []
        wp = tmdb(f"/movie/{res[0]['id']}/watch/providers", key, {}).get("results", {}).get(region, {})
        names = []
        for bucket in ("flatrate", "free", "ads"):
            for p in wp.get(bucket, []):
                c = canon(p.get("provider_name"))
                if c and c not in names:
                    names.append(c)
        return names[:4]
    except Exception:
        return []


def key_of(m):
    return f"{m.get('t','')}|{m.get('y','')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="IN")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.12)
    ap.add_argument("--files", default="data/catalog.json,data/movies.json")
    args = ap.parse_args()

    key = (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDBKEY") or "").strip()
    files = [f.strip() for f in args.files.split(",") if f.strip()]

    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            cache = {}

    # ---- stage 1: re-apply the cache (no key needed) ----
    applied = 0
    loaded = {}
    for f in files:
        if os.path.exists(f):
            loaded[f] = json.load(open(f, encoding="utf-8"))
    for f, data in loaded.items():
        for m in data:
            if not m.get("o") and cache.get(key_of(m)):
                m["o"] = cache[key_of(m)]
                applied += 1
    print(f"re-applied cached OTT to {applied} titles")

    if not key:
        for f, data in loaded.items():
            json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("TMDB_API_KEY not set — skipping new lookups (site keeps working).")
        return

    # ---- stage 2: look up the rest on TMDB ----
    todo = [(f, m) for f, data in loaded.items() for m in data if not m.get("o")]
    if args.limit:
        todo = todo[:args.limit]
    print(f"titles needing a new lookup: {len(todo)}")
    done = 0
    for f, m in todo:
        ck = key_of(m)
        if ck in cache:
            continue
        prov = providers_for(m.get("t", ""), m.get("y", ""), key, args.region)
        cache[ck] = prov
        time.sleep(args.delay)
        if prov:
            m["o"] = prov
            done += 1

    for f, data in loaded.items():
        json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(CACHE) or ".", exist_ok=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    filled = sum(1 for v in cache.values() if v)
    print(f"filled {done} new this run ({filled} known in cache)")


if __name__ == "__main__":
    main()
