#!/usr/bin/env python3
"""fetch_watch_providers.py — where each curated title actually streams, in India (TMDB).

TMDB's /watch/providers endpoint does not hand out a platform's own content id, so this fills
in what it really gives us: the accurate list of Indian subscription platforms for a title,
plus the JustWatch page. Both are free and keep working after the TMDB key is disconnected.

    TMDB_API_KEY=xxxx python3 scripts/fetch_watch_providers.py
"""
import argparse, glob, json, os, re, sys, time, urllib.parse, urllib.request

TMDB = "https://api.themoviedb.org/3"
OUT = "data/watch_providers.json"
REGION = "IN"
TARGETS = ["curated_hindi.json", "curated_hollywood.json", "curated_series.json",
           "curated_hollywood_series.json", "curated_anime.json", "curated_netflix.json",
           "curated_netflix_series.json", "curated_netflix_hollywood.json",
           "curated_prime.json", "curated_hotstar.json"]


def tmdb(path, key, params=None):
    q = dict(params or {})
    q["api_key"] = key
    url = f"{TMDB}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def norm(t):
    t = str(t or "").lower().replace("&", "and")
    t = re.sub(r"\b(the|a|an)\b", " ", re.sub(r"[^a-z0-9]+", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def lookup(title, year, is_series, key):
    kind = "tv" if is_series else "movie"
    params = {"query": title, "include_adult": "false"}
    if year:
        params["first_air_date_year" if is_series else "year"] = year
    try:
        d = tmdb(f"/search/{kind}", key, params)
    except Exception:
        return None
    hits = d.get("results") or []
    if not hits:
        return None
    tid = hits[0].get("id")
    try:
        wp = tmdb(f"/{kind}/{tid}/watch/providers", key)
    except Exception:
        return None
    block = (wp.get("results") or {}).get(REGION) or {}
    plats, seen = [], set()
    for bucket in ("flatrate", "free", "ads", "rent", "buy"):
        for p in block.get(bucket) or []:
            name = p.get("provider_name") or ""
            name = {"Amazon Prime Video": "Prime Video", "Disney+ Hotstar": "JioHotstar",
                    "JioHotstar": "JioHotstar", "Hotstar": "JioHotstar",
                    "Apple TV Plus": "Apple TV+", "Apple TV": "Apple TV+"}.get(name, name)
            if name and name not in seen:
                seen.add(name)
                plats.append(name)
    return {"p": plats, "jw": block.get("link") or "", "tmdb": tid}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=0.06)
    ap.add_argument("--limit", type=int, default=0, help="stop after N lookups (0 = all)")
    args = ap.parse_args()

    key = (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDBKEY") or "").strip()
    if not key:
        print("TMDB_API_KEY not set — skipping watch providers (site keeps working).")
        return

    out = {}
    if os.path.exists(OUT):
        try:
            out = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            out = {}

    todo = []
    for f in TARGETS:
        p = os.path.join("data", f)
        if not os.path.exists(p):
            continue
        try:
            for r in json.load(open(p, encoding="utf-8")):
                if r.get("t"):
                    todo.append(r)
        except Exception:
            continue
    print(f"titles to check: {len(todo):,} (already known: {len(out):,})")

    n = 0
    for r in todo:
        k = norm(r["t"])
        if not k or k in out:
            continue
        if args.limit and n >= args.limit:
            break
        res = lookup(r["t"], r.get("y"), r.get("type") == "Series", key)
        out[k] = res or {"p": [], "jw": ""}
        n += 1
        if n % 200 == 0:
            print(f"  {n:,} looked up")
            json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        time.sleep(args.delay)

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    withp = sum(1 for v in out.values() if v.get("p"))
    print(f"wrote {OUT}: {len(out):,} titles, {withp:,} with at least one Indian platform")


if __name__ == "__main__":
    main()
