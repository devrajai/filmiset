#!/usr/bin/env python3
"""fetch_tmdb_discover.py — pull a broad catalogue from TMDB (needs TMDB_API_KEY).

Goes well beyond the Wikidata sample: trending, popular, top-rated, now-playing and
upcoming movies + TV series, plus per-language discovery (Indian languages, Korean,
Japanese, English, …). Everything is written to data/tmdb.json, which the website
merges with the other sources.

    TMDB_API_KEY=xxxx python3 scripts/fetch_tmdb_discover.py --region IN
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

TMDB = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w342"
OUT = "data/tmdb.json"

LANGS = {
    "hi": "hindi", "gu": "gujarati-movie", "mr": "hindi", "bn": "hindi", "pa": "hindi",
    "ta": "south-dubbed", "te": "south-dubbed", "ml": "south-dubbed", "kn": "south-dubbed",
    "ko": "korean-dubbed", "ja": "anime", "en": "english-dubbed",
    "es": "english-dubbed", "fr": "english-dubbed", "tr": "english-dubbed", "zh": "english-dubbed",
}
AUDIO = {"hi": ["Hindi"], "gu": ["Gujarati"], "ta": ["Hindi (dub)", "Tamil"],
         "te": ["Hindi (dub)", "Telugu"], "ml": ["Hindi (dub)", "Malayalam"],
         "kn": ["Hindi (dub)", "Kannada"], "ko": ["Hindi (dub)", "Korean"],
         "ja": ["Hindi (dub)", "Japanese"]}

GENRE_MOOD = [("comedy", "Comedy"), ("drama", "Emotional"), ("action", "Action"),
              ("thriller", "Thriller"), ("mystery", "Mystery"), ("romance", "Romantic"),
              ("horror", "Horror"), ("music", "Feel-Good"), ("family", "Family"),
              ("adventure", "Action"), ("crime", "Thriller"), ("fantasy", "Action"),
              ("war", "Emotional"), ("history", "Emotional"), ("documentary", "Family"),
              ("animation", "Family"), ("science fiction", "Action")]


def tmdb(path, key, params=None):
    q = dict(params or {})
    q["api_key"] = key
    url = f"{TMDB}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def moods(genres):
    out = []
    for g in genres:
        gl = g.lower()
        for frag, mood in GENRE_MOOD:
            if frag in gl and mood not in out:
                out.append(mood)
    return out[:3]


def row(item, kind, gmap, lang):
    """kind: 'movie' | 'tv'"""
    is_tv = kind == "tv"
    title = item.get("title") or item.get("name") or ""
    date = (item.get("release_date") or item.get("first_air_date") or "")[:10]
    genres = [gmap[i] for i in (item.get("genre_ids") or []) if i in gmap][:3]
    if not genres:
        return None
    orig = item.get("original_language") or "en"
    cat = LANGS.get(orig, "english-dubbed")
    poster = item.get("poster_path")
    return {
        "t": title, "y": int(date[:4]) if date[:4].isdigit() else "",
        "cat": cat, "type": "Series" if is_tv else "Movie",
        "g": genres, "m": moods(genres),
        "a": AUDIO.get(orig, ["Hindi (dub)", "English"]),
        "o": [], "poster": (IMG + poster) if poster else "",
        "src": "tmdb", "status": "upcoming" if item.get("_upcoming") else "released",
        "date": date, "pop": int(item.get("vote_count") or 0),
        "rtg": round(float(item.get("vote_average") or 0), 1) or None,
        "vot": int(item.get("vote_count") or 0),
        "ov": (item.get("overview") or "")[:420],
        "tmdb": item.get("id"),
    }


def collect(key, region, pages):
    mg = {g["id"]: g["name"] for g in tmdb("/genre/movie/list", key).get("genres", [])}
    tg = {g["id"]: g["name"] for g in tmdb("/genre/tv/list", key).get("genres", [])}
    rows = []

    lists = [
        ("/trending/movie/day", "movie", mg, {}), ("/trending/movie/week", "movie", mg, {}),
        ("/trending/tv/day", "tv", tg, {}), ("/trending/tv/week", "tv", tg, {}),
        ("/movie/popular", "movie", mg, {}), ("/movie/top_rated", "movie", mg, {}),
        ("/movie/now_playing", "movie", mg, {"region": region}),
        ("/movie/upcoming", "movie", mg, {"region": region, "_upcoming": True}),
        ("/tv/popular", "tv", tg, {}), ("/tv/top_rated", "tv", tg, {}),
        ("/tv/on_the_air", "tv", tg, {}), ("/tv/airing_today", "tv", tg, {}),
    ]
    for path, kind, gmap, extra in lists:
        up = extra.pop("_upcoming", False)
        for page in range(1, pages + 1):
            try:
                d = tmdb(path, key, dict(extra, page=page))
            except Exception as e:
                print(f"  ! {path} p{page}: {type(e).__name__}", file=sys.stderr)
                continue
            for it in d.get("results", []):
                it["_upcoming"] = up
                r = row(it, kind, gmap, None)
                if r:
                    rows.append(r)
            time.sleep(0.05)

    for lang in LANGS:
        for kind, gmap in (("movie", mg), ("tv", tg)):
            for page in range(1, pages + 1):
                try:
                    d = tmdb(f"/discover/{kind}", key, {
                        "with_original_language": lang, "sort_by": "popularity.desc",
                        "vote_count.gte": 5, "page": page})
                except Exception as e:
                    print(f"  ! discover {kind}/{lang}: {type(e).__name__}", file=sys.stderr)
                    continue
                for it in d.get("results", []):
                    r = row(it, kind, gmap, lang)
                    if r:
                        rows.append(r)
                time.sleep(0.05)
    return rows


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        k = (r["t"].lower(), r["type"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="IN")
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    key = (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDBKEY") or "").strip()
    if not key:
        print("TMDB_API_KEY not set — writing an empty file (site keeps working).")
        rows = []
    else:
        try:
            rows = dedupe(collect(key, args.region, args.pages))
        except Exception as e:
            print(f"TMDB discover failed: {type(e).__name__} {e}", file=sys.stderr)
            rows = []
    print(f"collected {len(rows)} TMDB titles")
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    json.dump(rows, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
