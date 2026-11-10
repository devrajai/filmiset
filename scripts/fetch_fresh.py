#!/usr/bin/env python3
"""fetch_fresh.py — what is in cinemas now, what is coming, and what just landed on a platform.

Everything here comes from TMDB, which is the licensed source for release dates and streaming
availability. Nothing is scraped from a streaming or download site.

Seven queries, one file:

  /movie/now_playing?region=IN          what is in Indian cinemas this week
  /movie/upcoming?region=IN             what opens in the next six weeks
  /tv/on_the_air?region=IN              series with a new episode this week
  /watch/providers/movie?watch_region=IN   the real platform ids for India
  /discover/movie + /discover/tv per provider   what arrived on each platform
  /discover/movie?with_original_language=…      new Indian releases by language

The provider ids are looked up rather than hardcoded. The first version listed ten ids from memory
and eight of them returned nothing — Disney+ Hotstar, JioCinema, ZEE5, SonyLIV, HBO Max, MUBI all
came back empty for months because the ids were simply wrong for this region. Asking TMDB which
providers exist in India and what they are called cannot go stale.

    python3 fetch_fresh.py --out data/fresh.json.gz --days 30
"""
import argparse, datetime, gzip, json, os, sys, time, urllib.parse, urllib.request

TMDB = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w300"

# the platforms an Indian viewer actually uses, matched against the names TMDB returns
WANTED = ["Netflix", "Prime Video", "Disney Plus", "JioHotstar", "Jio Cinema", "ZEE5", "SonyLIV",
          "Apple TV", "HBO Max", "Crunchyroll", "MUBI", "aha", "Sun NXT", "Hoichoi", "Lionsgate Play",
          "Amazon miniTV", "ManoramaMAX", "ETV Win", "Discovery+", "DocuBay", "Chaupal"]

# Indian languages to sweep for new releases, most first
LANGS = [("hi", "Hindi"), ("ta", "Tamil"), ("te", "Telugu"), ("ml", "Malayalam"), ("kn", "Kannada"),
         ("bn", "Bengali"), ("mr", "Marathi"), ("pa", "Punjabi"), ("gu", "Gujarati"),
         ("or", "Odia"), ("as", "Assamese"), ("ur", "Urdu")]


def get(path, key, **params):
    q = urllib.parse.urlencode(dict(params, api_key=key, language="en-US"))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f"{TMDB}{path}?{q}", timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if attempt == 2:
                return None
            time.sleep(0.8 * (attempt + 1))
    return None


def shape(r, kind, provider=None):
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


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        k = r.get("tmdb")
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/fresh.json.gz")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--region", default="IN")
    a = ap.parse_args()

    key = os.environ.get("TMDB_API_KEY", "").strip()
    if not key:
        print("TMDB_API_KEY is not set"); sys.exit(1)

    today = datetime.date.today()
    since = (today - datetime.timedelta(days=a.days)).isoformat()
    until = (today + datetime.timedelta(days=45)).isoformat()

    out = {"updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "region": a.region, "since": since, "cinema": [], "upcoming": [],
           "ott": {}, "series": {}, "tvnow": {}, "bylang": {}}

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

    # ---- series with a new episode this week ----
    print("tv on the air…")
    d = get("/tv/on_the_air", key, region=a.region, page=1)
    if d and d.get("results"):
        out["tvnow"]["this week"] = [shape(r, "tv") for r in d["results"]][:30]
        print(f"  {len(out['tvnow']['this week'])} airing")

    # ---- the real Indian provider list ----
    print("providers for India…")
    prov = {}
    d = get("/watch/providers/movie", key, watch_region=a.region)
    for p in (d or {}).get("results", []):
        name = p.get("provider_name") or ""
        if any(w.lower() in name.lower() for w in WANTED):
            prov[p["provider_id"]] = name
    print(f"  {len(prov)} matched: {', '.join(sorted(prov.values()))[:120]}")

    for pid, name in sorted(prov.items()):
        films, shows = [], []
        for page in (1, 2):
            d = get("/discover/movie", key, with_watch_providers=pid, watch_region=a.region,
                    sort_by="primary_release_date.desc", page=page,
                    **{"primary_release_date.gte": since, "primary_release_date.lte": until,
                       "with_watch_monetization_types": "flatrate", "vote_count.gte": 3})
            if d and d.get("results"):
                films += [shape(r, "movie", name) for r in d["results"]]
        d = get("/discover/tv", key, with_watch_providers=pid, watch_region=a.region,
                sort_by="first_air_date.desc",
                **{"first_air_date.gte": since, "first_air_date.lte": until,
                   "with_watch_monetization_types": "flatrate", "vote_count.gte": 2})
        if d and d.get("results"):
            shows = [shape(r, "tv", name) for r in d["results"]]

        films, shows = dedupe(films)[:30], dedupe(shows)[:30]
        if films:
            out["ott"][name] = films
        if shows:
            out["series"][name] = shows
        print(f"  {name:20s} {len(films):>2} films  {len(shows):>2} series")
        time.sleep(0.2)

    # ---- new Indian releases by language, whether or not a platform is listed yet ----
    print("Indian languages…")
    for code, label in LANGS:
        d = get("/discover/movie", key, with_original_language=code,
                sort_by="primary_release_date.desc",
                **{"primary_release_date.gte": since, "primary_release_date.lte": until,
                   "vote_count.gte": 2})
        rows = []
        if d and d.get("results"):
            rows = dedupe([shape(r, "movie") for r in d["results"]])[:24]
        if rows:
            out["bylang"][label] = rows
        print(f"  {label:12s} {len(rows):>2}")
        time.sleep(0.2)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with gzip.open(a.out, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    ott = sum(len(v) for v in out["ott"].values())
    ser = sum(len(v) for v in out["series"].values())
    by = sum(len(v) for v in out["bylang"].values())
    print(f"\nwrote {a.out}  {os.path.getsize(a.out)/1024:.1f} KB")
    print(f"  cinema {len(out['cinema'])} · upcoming {len(out['upcoming'])} · "
          f"ott {ott} · series {ser} · indian {by}")


if __name__ == "__main__":
    main()
