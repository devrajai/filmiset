#!/usr/bin/env python3
"""fetch_fresh.py — what is in cinemas now, what is coming, and what just landed on a platform.

Everything here comes from TMDB, which is the licensed source for release dates and streaming
availability. Nothing is scraped from a streaming or download site.

Four queries, one file:

  /movie/now_playing?region=IN     what is in Indian cinemas this week
  /movie/upcoming?region=IN        what is coming in the next few weeks
  /discover/movie?with_watch_providers=…   what arrived on each platform recently
  /discover/tv?with_watch_providers=…      same, for series

The provider list is TMDB's own ids. A title can be on several, and the site shows it under each.

    python3 fetch_fresh.py --out data/fresh.json.gz --days 30
"""
import argparse, datetime, gzip, json, os, sys, time, urllib.parse, urllib.request

TMDB = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w300"

# TMDB watch-provider ids for the platforms an Indian viewer actually uses
PROVIDERS = {
    8:   "Netflix",
    119: "Prime Video",
    337: "Disney+ Hotstar",
    220: "JioCinema",
    232: "ZEE5",
    237: "SonyLIV",
    350: "Apple TV",
    1899: "HBO Max",
    283: "Crunchyroll",
    11:  "MUBI",
}

def get(path, key, **params):
    q = urllib.parse.urlencode(dict(params, api_key=key, language="en-US"))
    url = f"{TMDB}{path}?{q}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if attempt == 2:
                return None
            time.sleep(0.8 * (attempt + 1))
    return None

def shape(r, kind, provider=None):
    """One row in the shape the site already understands."""
    title = r.get("title") or r.get("name") or ""
    date = r.get("release_date") or r.get("first_air_date") or ""
    poster = r.get("poster_path")
    return {
        "t": title,
        "y": int(date[:4]) if date[:4].isdigit() else "",
        "date": date,
        "ov": (r.get("overview") or "")[:400],
        "r": round((r.get("vote_average") or 0), 1),
        "v": r.get("vote_count") or 0,
        "poster": (IMG + poster) if poster else "",
        "type": "Series" if kind == "tv" else "Movie",
        "tmdb": r.get("id"),
        "lang": (r.get("original_language") or ""),
        "platform": provider or "",
        "src": "tmdb",
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/fresh.json.gz")
    ap.add_argument("--days", type=int, default=30, help="how far back to look for platform arrivals")
    ap.add_argument("--region", default="IN")
    a = ap.parse_args()

    key = os.environ.get("TMDB_API_KEY", "").strip()
    if not key:
        print("TMDB_API_KEY is not set"); sys.exit(1)

    today = datetime.date.today()
    since = (today - datetime.timedelta(days=a.days)).isoformat()
    until = (today + datetime.timedelta(days=45)).isoformat()

    out = {"updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "region": a.region, "since": since, "cinema": [], "upcoming": [], "ott": {}, "series": {}}

    # ---- in cinemas now ----
    print("cinema…")
    d = get("/movie/now_playing", key, region=a.region, page=1)
    if d and d.get("results"):
        out["cinema"] = [shape(r, "movie") for r in d["results"]][:40]
        print(f"  {len(out['cinema'])} in cinemas")

    # ---- coming ----
    print("upcoming…")
    d = get("/movie/upcoming", key, region=a.region, page=1)
    if d and d.get("results"):
        rows = [shape(r, "movie") for r in d["results"]]
        rows = [r for r in rows if r["date"] and r["date"] >= today.isoformat()]
        rows.sort(key=lambda r: r["date"])
        out["upcoming"] = rows[:40]
        print(f"  {len(out['upcoming'])} coming")

    # ---- new on each platform ----
    for pid, name in PROVIDERS.items():
        # films
        d = get("/discover/movie", key,
                with_watch_providers=pid, watch_region=a.region,
                sort_by="primary_release_date.desc",
                **{"primary_release_date.gte": since,
                   "primary_release_date.lte": until,
                   "with_watch_monetization_types": "flatrate",
                   "vote_count.gte": 5})
        films = []
        if d and d.get("results"):
            films = [shape(r, "movie", name) for r in d["results"]][:24]
        # series
        d = get("/discover/tv", key,
                with_watch_providers=pid, watch_region=a.region,
                sort_by="first_air_date.desc",
                **{"first_air_date.gte": since, "first_air_date.lte": until,
                   "with_watch_monetization_types": "flatrate",
                   "vote_count.gte": 3})
        shows = []
        if d and d.get("results"):
            shows = [shape(r, "tv", name) for r in d["results"]][:24]
        if films: out["ott"][name] = films
        if shows: out["series"][name] = shows
        print(f"  {name:16s} {len(films):>2} films  {len(shows):>2} series")
        time.sleep(0.25)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with gzip.open(a.out, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\nwrote {a.out}  {os.path.getsize(a.out)/1024:.1f} KB")
    print(f"  cinema {len(out['cinema'])} · upcoming {len(out['upcoming'])} · "
          f"ott {sum(len(v) for v in out['ott'].values())} · "
          f"series {sum(len(v) for v in out['series'].values())}")

if __name__ == "__main__":
    main()
