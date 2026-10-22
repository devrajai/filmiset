#!/usr/bin/env python3
"""fetch_ott.py — fill OTT availability ("which platform is this on?") using TMDB.

TMDB's watch-provider data is the reliable free source, but it needs a **free API key**.
Set it as an environment variable / GitHub secret named TMDB_API_KEY, then:

    TMDB_API_KEY=xxxxxxxx python3 scripts/fetch_ott.py --region IN

If no key is present the script does nothing and exits 0, so the daily workflow
keeps working without it.

It only fills titles that have no OTT info yet, and caches lookups in
data/ott_cache.json so re-runs are cheap.
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

TMDB = "https://api.themoviedb.org/3"
CACHE = "data/ott_cache.json"

# TMDB provider name -> our label
PROVIDER_MAP = {
    "netflix": "Netflix",
    "amazon prime video": "Prime Video",
    "amazon video": "Prime Video",
    "prime video": "Prime Video",
    "jiohotstar": "JioHotstar",
    "disney+ hotstar": "JioHotstar",
    "hotstar": "JioHotstar",
    "jiocinema": "JioCinema",
    "zee5": "ZEE5",
    "sonyliv": "SonyLIV",
    "sony liv": "SonyLIV",
    "hbo max": "HBO Max",
    "jiohbo": "HBO Max",
    "apple tv+": "Apple TV+",
    "apple tv plus": "Apple TV+",
    "crunchyroll": "Crunchyroll",
    "mx player": "MX Player",
    "youtube": "YouTube",
    "aha": "Aha",
    "sun nxt": "Sun NXT",
    "hoichoi": "Hoichoi",
    "lionsgate play": "Lionsgate Play",
    "discovery+": "Discovery+",
    "discovery plus": "Discovery+",
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
    """Return a list of platform labels, or [] if none / not found."""
    try:
        params = {"query": title, "include_adult": "false"}
        if year:
            params["year"] = str(year)
        res = tmdb("/search/movie", key, params).get("results", [])
        if not res:
            res = tmdb("/search/movie", key, {"query": title}).get("results", [])
        if not res:
            return []
        mid = res[0]["id"]
        wp = tmdb(f"/movie/{mid}/watch/providers", key, {}).get("results", {}).get(region, {})
        names = []
        for bucket in ("flatrate", "free", "ads"):
            for p in wp.get(bucket, []):
                c = canon(p.get("provider_name"))
                if c and c not in names:
                    names.append(c)
        return names[:4]
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="IN")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.12)
    ap.add_argument("--files", default="data/catalog.json,data/movies.json")
    args = ap.parse_args()

    key = (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDBKEY") or "").strip()
    if not key:
        print("TMDB_API_KEY not set — skipping OTT enrichment (site keeps working).")
        return

    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            cache = {}

    files = [f.strip() for f in args.files.split(",") if f.strip()]
    todo = []
    for f in files:
        if not os.path.exists(f):
            continue
        data = json.load(open(f, encoding="utf-8"))
        for m in data:
            if m.get("o"):
                continue
            todo.append((f, m))
    if args.limit:
        todo = todo[:args.limit]
    print(f"titles needing OTT info: {len(todo)}")

    done = 0
    for f, m in todo:
        ck = f"{m.get('t','')}|{m.get('y','')}"
        if ck in cache:
            prov = cache[ck]
        else:
            prov = providers_for(m.get("t", ""), m.get("y", ""), key, args.region)
            cache[ck] = prov
            time.sleep(args.delay)
        if prov:
            m["o"] = prov
            done += 1

    for f in files:
        if os.path.exists(f):
            data = json.load(open(f, encoding="utf-8"))
            for m in data:
                ck = f"{m.get('t','')}|{m.get('y','')}"
                if not m.get("o") and cache.get(ck):
                    m["o"] = cache[ck]
            json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    os.makedirs(os.path.dirname(CACHE) or ".", exist_ok=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    filled = sum(1 for v in cache.values() if v)
    print(f"filled OTT for {done} titles this run ({filled} known in cache)")


if __name__ == "__main__":
    main()
