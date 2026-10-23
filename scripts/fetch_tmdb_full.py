#!/usr/bin/env python3
"""fetch_tmdb_full.py — sweep TMDB's whole catalogue (movies + TV) into one gzipped file.

TMDB holds roughly 1M movies and 250k TV shows. `/discover` only returns 500 pages per
query, so we sweep **year by year** (every year × up to N pages) which covers the catalogue
evenly, newest and oldest alike.

Posters are stored as **public image.tmdb.org URLs** — hot-linked, never downloaded, so they
cost us no storage and keep working after the TMDB API key is disconnected.

    TMDB_API_KEY=xxxx python3 scripts/fetch_tmdb_full.py --start-year 1950 --end-year 2026 --max-pages 100
"""
import argparse, gzip, json, os, sys, time, urllib.parse, urllib.request

TMDB = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w300"
OUT = "data/tmdb_full.json.gz"

LANG_CAT = {
    "hi": "hindi", "gu": "gujarati-movie", "mr": "hindi", "bn": "hindi", "pa": "hindi",
    "ta": "south-dubbed", "te": "south-dubbed", "ml": "south-dubbed", "kn": "south-dubbed",
    "ko": "korean-dubbed", "ja": "anime", "en": "english-dubbed",
}


def tmdb(path, key, params=None):
    q = dict(params or {})
    q["api_key"] = key
    url = f"{TMDB}{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-year", type=int, default=1950)
    ap.add_argument("--end-year", type=int, default=2026)
    ap.add_argument("--max-pages", type=int, default=100, help="pages per year (20 titles each)")
    ap.add_argument("--delay", type=float, default=0.06)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    key = (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDBKEY") or "").strip()
    if not key:
        print("TMDB_API_KEY not set — writing an empty file (site keeps working).")
        json.dump([], open(args.out.replace(".gz", ""), "w"))
        with gzip.open(args.out, "wt", encoding="utf-8") as f:
            json.dump([], f)
        return

    mg = {g["id"]: g["name"] for g in tmdb("/genre/movie/list", key).get("genres", [])}
    tg = {g["id"]: g["name"] for g in tmdb("/genre/tv/list", key).get("genres", [])}

    seen, rows = set(), []
    reqs = 0
    for kind, gmap, date_key in (("movie", mg, "primary_release_year"), ("tv", tg, "first_air_date_year")):
        for year in range(args.start_year, args.end_year + 1):
            empty = 0
            for page in range(1, args.max_pages + 1):
                try:
                    d = tmdb(f"/discover/{kind}", key,
                             {date_key: year, "sort_by": "popularity.desc", "page": page,
                              "include_adult": "false"})
                    reqs += 1
                except Exception as e:
                    print(f"  ! {kind} {year} p{page}: {type(e).__name__}", file=sys.stderr)
                    break
                results = d.get("results", [])
                if not results:
                    empty += 1
                    if empty > 1:
                        break
                    continue
                for it in results:
                    tid = it.get("id")
                    if not tid or tid in seen:
                        continue
                    seen.add(tid)
                    date = (it.get("release_date") or it.get("first_air_date") or "")[:10]
                    genres = [gmap[i] for i in (it.get("genre_ids") or []) if i in gmap][:3]
                    if not genres:
                        continue
                    orig = it.get("original_language") or "en"
                    rows.append({
                        "id": "tmdb-" + str(tid),
                        "t": it.get("title") or it.get("name") or "",
                        "y": int(date[:4]) if date[:4].isdigit() else "",
                        "type": "Series" if kind == "tv" else "Movie",
                        "g": genres,
                        "rtg": round(float(it.get("vote_average") or 0), 1) or "",
                        "vot": int(it.get("vote_count") or 0),
                        "poster": (IMG + it["poster_path"]) if it.get("poster_path") else "",
                        "cat": LANG_CAT.get(orig, "english-dubbed"),
                        "ov": (it.get("overview") or "")[:300],
                    })
                time.sleep(args.delay)
            if year % 10 == 0:
                print(f"  {kind} {year}: {len(rows):,} rows so far ({reqs:,} requests)")

    rows.sort(key=lambda r: -r["vot"])
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with gzip.open(args.out, "wt", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    mb = os.path.getsize(args.out) / 1048576
    withp = sum(1 for r in rows if r["poster"])
    print(f"wrote {args.out}: {len(rows):,} TMDB titles, {withp:,} with a poster ({mb:.1f} MB, {reqs:,} requests)")


if __name__ == "__main__":
    main()
