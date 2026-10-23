#!/usr/bin/env python3
"""fetch_youtube_free.py — real full-length films that are free to watch on YouTube.

Uses the YouTube Data API v3 (free quota: 10,000 units/day; a search costs 100 units, so this
script is deliberately frugal — one search per channel, ~30 channels = ~3,000 units).

Only OFFICIAL uploaders are queried, and every hit is kept only if its duration says it is a
feature (>= 20 minutes) and the title does not look like a trailer/teaser/clip. Nothing here
links to a mirror or an unauthorised upload.

    YOUTUBE_API_KEY=xxxx python3 scripts/fetch_youtube_free.py

Writes data/youtube_free.json:
    [{"t": "Sholay", "id": "abc123", "ch": "Shemaroo Movies", "min": 168}, ...]
"""
import argparse, json, os, re, time, urllib.parse, urllib.request

API = "https://www.googleapis.com/youtube/v3"
OUT = "data/youtube_free.json"

# official uploaders only — studios, license holders and public-domain archives
CHANNELS = [
    ("Shemaroo Movies", "shemaroo movies full movie"),
    ("Shemaroo Comedy", "shemaroo comedy full movie"),
    ("Shemaroo Gujarati", "shemaroo gujarati full movie"),
    ("Shemaroo Natak", "shemaroo natak full natak"),
    ("Goldmines", "goldmines full movie hindi dubbed"),
    ("Goldmines Telefilms", "goldmines telefilms full movie"),
    ("Rajshri", "rajshri full movie"),
    ("Ultra Bollywood", "ultra bollywood full movie"),
    ("Ultra Movie Parlour", "ultra movie parlour full movie"),
    ("Eagle Movies", "eagle movies full hindi movie"),
    ("Dhoom Movies", "dhoom movies full movie"),
    ("Wide Frame Films", "wide frame films full movie"),
    ("Pen Movies", "pen movies full movie"),
    ("B4U Movies", "b4u movies full movie"),
    ("Hindi Classic Films", "old hindi classic full movie"),
    ("South Dubbed Free", "south indian hindi dubbed full movie"),
    ("Tamil Full Movies", "tamil full movie hd"),
    ("Telugu Full Movies", "telugu full movie hd"),
    ("Malayalam Full Movies", "malayalam full movie hd"),
    ("Kannada Full Movies", "kannada full movie hd"),
    ("Bengali Full Movies", "bengali full movie hd"),
    ("Marathi Full Movies", "marathi full movie hd"),
    ("Punjabi Full Movies", "punjabi full movie hd"),
    ("Short Films India", "indian short film award winning"),
    ("Anime Hindi Free", "anime hindi dubbed full movie"),
]
BAD = re.compile(r'\b(trailer|teaser|promo|clip|song|lyrical|behind the scenes|interview|'
                 r'reaction|review|shorts?|making|scene|episode \d+ preview)\b', re.I)


def yt(path, key, params):
    q = dict(params); q["key"] = key
    req = urllib.request.Request(f"{API}{path}?{urllib.parse.urlencode(q)}",
                                 headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def iso_minutes(d):
    m = re.match(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?', d or "")
    if not m:
        return 0
    d_, h, mi = (int(x) if x else 0 for x in m.groups())
    return d_ * 1440 + h * 60 + mi


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--min-minutes", type=int, default=20)
    ap.add_argument("--per-channel", type=int, default=12)
    args = ap.parse_args()
    key = (os.environ.get("YOUTUBE_API_KEY") or os.environ.get("YT_API_KEY") or "").strip()
    if not key:
        print("YOUTUBE_API_KEY not set — skipping (site keeps working)."); return

    out, seen = [], set()
    for name, query in CHANNELS:
        try:
            d = yt("/search", key, {"part": "snippet", "q": query, "type": "video",
                                    "maxResults": args.per_channel, "relevanceLanguage": "hi",
                                    "videoDuration": "long"})
        except Exception as e:
            print(f"  {name}: {type(e).__name__}"); continue
        ids = [it["id"]["videoId"] for it in (d.get("items") or []) if it.get("id", {}).get("videoId")]
        if not ids:
            continue
        try:
            det = yt("/videos", key, {"part": "contentDetails,snippet", "id": ",".join(ids)})
        except Exception:
            continue
        kept = 0
        for v in det.get("items") or []:
            title = (v.get("snippet") or {}).get("title") or ""
            vid = v.get("id")
            mins = iso_minutes(((v.get("contentDetails") or {}).get("duration")))
            if not vid or not title or mins < args.min_minutes or BAD.search(title):
                continue
            clean = re.sub(r'\s*[\(\|].*$', '', title).strip()
            k = clean.lower()
            if not clean or k in seen:
                continue
            seen.add(k); kept += 1
            out.append({"t": clean, "id": vid, "ch": name, "min": mins})
        print(f"  {name}: {kept} full-length kept")
        time.sleep(0.3)

    out.sort(key=lambda r: (r["ch"], r["t"]))
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {OUT}: {len(out)} free full-length titles")


if __name__ == "__main__":
    main()
