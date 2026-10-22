#!/usr/bin/env python3
"""fetch_tmdb.py — enrich the catalogue with TMDB data (needs a free TMDB_API_KEY).

Adds, for each title:
  o    OTT platforms (India watch providers)
  rt   runtime in minutes
  rtg  TMDB rating (0-10)
  vot  TMDB vote count
  cert India age certification (U / U/A 7+ / U/A 13+ / U/A 16+ / A)
  tr   YouTube trailer id

Two stages:
  1. Re-apply everything already known from data/tmdb_cache.json (no key needed).
     Important because fetch_data.py regenerates the catalogue and resets these fields.
  2. Look up the rest on TMDB.

If no key is present, stage 1 still runs and the script exits 0.

    TMDB_API_KEY=xxxx python3 scripts/fetch_tmdb.py --region IN
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

TMDB = "https://api.themoviedb.org/3"
CACHE = "data/tmdb_cache.json"
FIELDS = ("o", "rt", "rtg", "vot", "cert", "tr", "imdb")

PROVIDER_MAP = {
    "netflix": "Netflix", "amazon prime video": "Prime Video", "amazon video": "Prime Video",
    "prime video": "Prime Video", "jiohotstar": "JioHotstar", "disney+ hotstar": "JioHotstar",
    "hotstar": "JioHotstar", "jiocinema": "JioCinema", "zee5": "ZEE5", "sonyliv": "SonyLIV",
    "sony liv": "SonyLIV", "hbo max": "HBO Max", "jiohbo": "HBO Max", "apple tv+": "Apple TV+",
    "apple tv plus": "Apple TV+", "crunchyroll": "Crunchyroll", "mx player": "MX Player",
    "youtube": "YouTube", "aha": "Aha", "sun nxt": "Sun NXT", "hoichoi": "Hoichoi",
    "lionsgate play": "Lionsgate Play", "discovery+": "Discovery+", "discovery plus": "Discovery+",
}

FAMILY_CERTS = {"U", "U/A", "U/A 7+", "U/A 13+", "G", "PG", "PG-13", "TV-PG", "TV-G", "TV-Y7"}


def canon(name):
    return PROVIDER_MAP.get((name or "").strip().lower())


def tmdb(path, key, params=None):
    q = dict(params or {})
    q["api_key"] = key
    url = f"{TMDB}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def lookup(title, year, key, region):
    """Return a dict with any of FIELDS we could find ({} on failure)."""
    out = {}
    try:
        params = {"query": title, "include_adult": "false"}
        if year:
            params["year"] = str(year)
        res = tmdb("/search/movie", key, params).get("results", [])
        if not res:
            res = tmdb("/search/movie", key, {"query": title}).get("results", [])
        if not res:
            return out
        mid = res[0]["id"]

        d = tmdb(f"/movie/{mid}", key, {"append_to_response": "release_dates,videos"})
        if d.get("imdb_id"):
            out["imdb"] = d["imdb_id"]
        if d.get("runtime"):
            out["rt"] = int(d["runtime"])
        if d.get("vote_average"):
            out["rtg"] = round(float(d["vote_average"]), 1)
        if d.get("vote_count"):
            out["vot"] = int(d["vote_count"])
        for entry in (d.get("release_dates", {}) or {}).get("results", []):
            if entry.get("iso_3166_1") == region:
                certs = [x.get("certification") for x in entry.get("release_dates", []) if x.get("certification")]
                if certs:
                    out["cert"] = certs[0]
                break
        for v in (d.get("videos", {}) or {}).get("results", []):
            if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser"):
                out["tr"] = v.get("key")
                if v.get("type") == "Trailer":
                    break

        wp = tmdb(f"/movie/{mid}/watch/providers", key, {}).get("results", {}).get(region, {})
        names = []
        for bucket in ("flatrate", "free", "ads"):
            for p in wp.get(bucket, []):
                c = canon(p.get("provider_name"))
                if c and c not in names:
                    names.append(c)
        if names:
            out["o"] = names[:4]
    except Exception:
        pass
    return out


def key_of(m):
    return f"{m.get('t','')}|{m.get('y','')}"


def normalise(v):
    """Old cache stored a bare list of providers; new cache stores a dict."""
    if isinstance(v, list):
        return {"o": v} if v else {}
    return v if isinstance(v, dict) else {}


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
            cache = {k: normalise(v) for k, v in json.load(open(CACHE, encoding="utf-8")).items()}
        except Exception:
            cache = {}
    elif os.path.exists("data/ott_cache.json"):          # migrate the old cache
        try:
            cache = {k: normalise(v) for k, v in json.load(open("data/ott_cache.json", encoding="utf-8")).items()}
        except Exception:
            cache = {}

    loaded = {f: json.load(open(f, encoding="utf-8")) for f in files if os.path.exists(f)}

    applied = 0
    for f, data in loaded.items():
        for m in data:
            info = cache.get(key_of(m))
            if not info:
                continue
            for k in FIELDS:
                if info.get(k) and not m.get(k):
                    m[k] = info[k]
                    applied += 1
    print(f"re-applied cached TMDB data ({applied} fields)")

    if not key:
        for f, data in loaded.items():
            json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("TMDB_API_KEY not set — skipping new lookups (site keeps working).")
        return

    todo = [(f, m) for f, data in loaded.items() for m in data if not m.get("rt")]
    if args.limit:
        todo = todo[:args.limit]
    print(f"titles needing a new lookup: {len(todo)}")
    done = 0
    for f, m in todo:
        ck = key_of(m)
        if ck in cache:
            continue
        info = lookup(m.get("t", ""), m.get("y", ""), key, args.region)
        cache[ck] = info
        time.sleep(args.delay)
        if info:
            for k in FIELDS:
                if info.get(k):
                    m[k] = info[k]
            done += 1

    for f, data in loaded.items():
        json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(CACHE) or ".", exist_ok=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"enriched {done} titles this run ({sum(1 for v in cache.values() if v)} known in cache)")


if __name__ == "__main__":
    main()
