#!/usr/bin/env python3
"""fetch_youtube.py — collect movie/trailer videos from YouTube channels.

FREE, no API key: uses each channel's public RSS feed
  https://www.youtube.com/feeds/videos.xml?channel_id=UC...
A channel handle (@Name) is resolved to its channel id by reading the channel page.

Channels are listed in channels.txt:
    # handle-or-channel-id | category | original-language | display name
    ShemarooGujarati | gujarati-movie | Gujarati | Shemaroo Gujarati

Output: data/youtube.json  (cards with a video thumbnail + trailer link)
"""
import argparse, html, json, os, re, sys, time, urllib.parse, urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

STOPWORDS = {"movie", "movies", "film", "films", "scene", "scenes", "full", "new",
             "gujarati", "hindi", "best", "of", "song", "video", "promo", "trailer",
             "teaser", "anniversary", "official", "hd", "4k", "shorts", "clip",
             "natak", "comedy", "action", "superhit", "blockbuster", "latest"}


def get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def resolve_channel_id(name):
    name = name.strip()
    if re.fullmatch(r"UC[\w-]{20,}", name):
        return name
    handle = name.lstrip("@")
    for url in (f"https://www.youtube.com/@{handle}", f"https://www.youtube.com/c/{handle}",
                f"https://www.youtube.com/user/{handle}"):
        try:
            h = get(url)
        except Exception:
            continue
        m = re.search(r'"channelId":"(UC[\w-]{20,})"', h) or re.search(r'channel/(UC[\w-]{20,})', h)
        if m:
            return m.group(1)
        time.sleep(0.3)
    return None


def clean(s):
    s = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]", " ", s)   # emoji / ZWJ
    s = html.unescape(s)
    s = re.sub(r"@[A-Za-z0-9_.-]{2,}", " ", s)                       # @channel mentions
    return re.sub(r"\s+", " ", s).strip()


def extract_name(title):
    """Best-effort movie name from a YouTube video title."""
    t = clean(title)
    segs = [clean(x) for x in t.split("|") if clean(x)]
    if not segs:
        return t[:80]
    best, best_score = segs[0], -99
    for s in segs:
        words = re.findall(r"[A-Za-z][A-Za-z'&.]+", s)
        latin = [w for w in words if len(w) >= 3 and w.lower() not in STOPWORDS]
        score = len(latin) * 2
        if re.search(r"\b(trailer|teaser|promo|first look|motion poster|coming soon)\b", s, re.I):
            score += 3
        if len(words) and len(latin) / max(len(words), 1) < 0.25:
            score -= 4                                     # mostly non-Latin (hook text)
        if len(s) > 60:
            score -= 1
        if score > best_score:
            best, best_score = s, score
    name = re.split(r"\s+[-–]\s+", best)[0].strip(" -–|,.")
    if not name or len(name) < 3:
        name = best
    return name[:70]


def fetch_channel(handle, cat, lang, label, limit):
    cid = resolve_channel_id(handle)
    if not cid:
        print(f"  ! {handle}: channel id not found", file=sys.stderr)
        return []
    try:
        xml = get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
    except Exception as e:
        print(f"  ! {handle}: {type(e).__name__}", file=sys.stderr)
        return []
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S)[:limit]:
        tm = re.search(r"<title>(.*?)</title>", e, re.S)
        vm = re.search(r"<yt:videoId>(.*?)</yt:videoId>", e)
        pm = re.search(r"<published>(.*?)</published>", e)
        if not (tm and vm):
            continue
        vid = vm.group(1)
        published = pm.group(1)[:10] if pm else ""
        raw_title = clean(tm.group(1))
        name = extract_name(raw_title)
        upcoming = bool(re.search(r"\b(trailer|teaser|first look|motion poster|coming soon|announcement)\b",
                                  raw_title, re.I))
        out.append({
            "t": name, "y": int(published[:4]) if published[:4].isdigit() else "",
            "cat": cat, "type": "Movie", "g": [], "m": [], "a": [lang], "o": ["YouTube"],
            "poster": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "trailer": f"https://www.youtube.com/watch?v={vid}",
            "src": "youtube", "channel": label,
            "status": "upcoming" if upcoming else "released",
            "date": published, "note": raw_title[:160],
        })
    print(f"  {label or handle:26s} -> {len(out)} videos")
    return out


def read_channels(path):
    rows = []
    if not os.path.exists(path):
        return rows
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        parts += [""] * (4 - len(parts))
        rows.append(parts[:4])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channels", default="channels.txt")
    ap.add_argument("--out", default="data/youtube.json")
    ap.add_argument("--per-channel", type=int, default=12)
    args = ap.parse_args()

    rows = read_channels(args.channels)
    if not rows:
        print(f"no channels in {args.channels}", file=sys.stderr)
        return
    print(f"Reading {len(rows)} channels…")
    videos = []
    for handle, cat, lang, label in rows:
        if handle:
            videos += fetch_channel(handle, cat or "hindi", lang or "Hindi", label, args.per_channel)
        time.sleep(0.4)

    # de-dup by video title (keep the newest)
    seen, uniq = set(), []
    for v in sorted(videos, key=lambda x: x.get("date", ""), reverse=True):
        k = v["t"].lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(v)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    json.dump(uniq, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {len(uniq)} YouTube entries -> {args.out}")


if __name__ == "__main__":
    main()
