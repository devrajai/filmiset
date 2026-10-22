#!/usr/bin/env python3
"""fetch_jikan.py — anime catalogue from Jikan (MyAnimeList), free, no API key.

Writes data/jikan.json, which the website merges with the other sources.
Jikan allows ~3 requests/second, so we sleep between calls.

    python3 scripts/fetch_jikan.py
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

API = "https://api.jikan.moe/v4"
OUT = "data/jikan.json"
UA = "FilmiSetBot/1.0 (https://github.com/devrajai/filmiset)"

MOOD_MAP = [("comedy", "Comedy"), ("drama", "Emotional"), ("action", "Action"),
            ("thriller", "Thriller"), ("mystery", "Mystery"), ("romance", "Romantic"),
            ("horror", "Horror"), ("music", "Feel-Good"), ("family", "Family"),
            ("adventure", "Action"), ("fantasy", "Action"), ("sci-fi", "Action"),
            ("sports", "Feel-Good"), ("slice of life", "Family")]


def get(path, params=None):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def moods(genres):
    out = []
    for g in genres:
        gl = g.lower()
        for frag, mood in MOOD_MAP:
            if frag in gl and mood not in out:
                out.append(mood)
    return out[:3]


def row(a):
    title = a.get("title_english") or a.get("title") or ""
    if not title:
        return None
    genres = [g.get("name") for g in (a.get("genres") or []) if g.get("name")][:3]
    if not genres:
        genres = [g.get("name") for g in (a.get("themes") or []) if g.get("name")][:3] or ["Animation"]
    date = ((a.get("aired") or {}).get("from") or "")[:10]
    studios = [s.get("name") for s in (a.get("studios") or []) if s.get("name")]
    syn = (a.get("synopsis") or "").replace("[Written by MAL Rewrite]", "").strip()
    poster = ((a.get("images") or {}).get("jpg") or {}).get("large_image_url") \
        or ((a.get("images") or {}).get("jpg") or {}).get("image_url") or ""
    is_movie = (a.get("type") or "") == "Movie"
    return {
        "t": title, "y": a.get("year") or (int(date[:4]) if date[:4].isdigit() else ""),
        "cat": "anime", "cats": ["anime", "animation"],
        "type": "Movie" if is_movie else "Series",
        "g": genres, "m": moods(genres) or ["Action"],
        "a": ["Hindi (dub)", "Japanese"], "o": [],
        "poster": poster, "src": "jikan",
        "status": "upcoming" if (a.get("status") or "").startswith("Not yet") else "released",
        "date": date, "pop": int(a.get("scored_by") or 0),
        "rtg": round(float(a.get("score") or 0), 1) or None,
        "vot": int(a.get("scored_by") or 0),
        "ov": syn[:420], "prod": studios[0] if studios else "", "dir": "",
        "mal": a.get("mal_id"),
    }


def collect(pages):
    rows = []
    sources = [
        ("/top/anime", {"filter": "bypopularity"}),
        ("/top/anime", {"filter": "byscore"}),
        ("/top/anime", {"filter": "airing"}),
        ("/top/anime", {"filter": "favorite"}),
        ("/seasons/now", {}),
        ("/seasons/upcoming", {}),
    ]
    for path, params in sources:
        for page in range(1, pages + 1):
            try:
                d = get(path, dict(params, limit=25, page=page))
            except Exception as e:
                print(f"  ! {path} {params} p{page}: {type(e).__name__}", file=sys.stderr)
                time.sleep(1.0)
                continue
            for a in d.get("data", []):
                r = row(a)
                if r:
                    rows.append(r)
            time.sleep(0.45)
    return rows


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        k = r["t"].lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=4)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    try:
        rows = dedupe(collect(args.pages))
    except Exception as e:
        print(f"Jikan unavailable ({type(e).__name__}) — skipping anime source.", file=sys.stderr)
        return
    print(f"collected {len(rows)} anime from Jikan")
    if not rows:
        return
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    json.dump(rows, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
