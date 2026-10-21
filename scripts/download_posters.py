#!/usr/bin/env python3
"""download_posters.py — download poster images, compress them, and store them
locally under posters/ so the site no longer hotlinks Wikipedia.

For every poster URL found in data/catalog.json, data/movies.json and index.html:
  * download it
  * resize to 300px wide, re-encode as JPEG (quality 70)  -> big size win
  * save to  posters/<slug>.jpg
  * rewrite the JSON / HTML so 'poster' points at the local file

Re-running is safe: images already on disk are skipped (resume).
"""
import argparse, hashlib, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

UA = "FilmiSetBot/1.0 (https://github.com/devrajai/filmiset)"
OUTDIR = "posters"
WIDTH = 300
QUALITY = 70


def slug_for(url, used):
    name = urllib.parse.unquote(url.split("?")[0].rstrip("/").split("/")[-1])
    name = re.sub(r"\.[A-Za-z0-9]+$", "", name)            # drop extension
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48] or "poster"
    if slug in used and used[slug] != url:                 # collision -> add hash
        slug = slug + "-" + hashlib.md5(url.encode()).hexdigest()[:6]
    used[slug] = url
    return slug


def collect_urls():
    urls = []
    for f in ("data/catalog.json", "data/movies.json"):
        if not os.path.exists(f):
            continue
        for m in json.load(open(f, encoding="utf-8")):
            p = m.get("poster") or ""
            if p.startswith("http"):
                urls.append(p)
    if os.path.exists("index.html"):
        html = open("index.html", encoding="utf-8").read()
        urls += re.findall(r"poster:'(https?://[^']+)'", html)
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def fetch_one(url, used, delay=0.0):
    from io import BytesIO
    slug = slug_for(url, used)
    dest = os.path.join(OUTDIR, slug + ".jpg")
    if os.path.exists(dest):
        return url, "posters/" + slug + ".jpg", "cached"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            raw = urllib.request.urlopen(req, timeout=45).read()
            im = Image.open(BytesIO(raw))
            if im.mode != "RGB":
                im = im.convert("RGB")
            w, h = im.size
            if w > WIDTH:
                im = im.resize((WIDTH, int(h * WIDTH / w)), Image.LANCZOS)
            im.save(dest, "JPEG", quality=QUALITY, optimize=True)
            if delay:
                time.sleep(delay)
            return url, "posters/" + slug + ".jpg", "ok"
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(3 + 3 * attempt)
                continue
            return url, None, f"ERR {e.code}"
        except Exception as e:
            return url, None, f"ERR {type(e).__name__}"
    return url, None, "ERR 429"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--delay", type=float, default=0.4, help="seconds to wait after each request")
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    urls = collect_urls()
    if args.limit:
        urls = urls[:args.limit]
    print(f"poster URLs: {len(urls)}")

    used, mapping = {}, {}
    ok = cached = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for url, local, status in ex.map(lambda u: fetch_one(u, used, args.delay), urls):
            if local:
                mapping[url] = local
                cached += 1 if status == "cached" else 0
                ok += 1 if status == "ok" else 0
            else:
                fail += 1
    print(f"  ok={ok} cached={cached} fail={fail}")

    # rewrite data files
    for f in ("data/catalog.json", "data/movies.json"):
        if not os.path.exists(f):
            continue
        data = json.load(open(f, encoding="utf-8"))
        n = 0
        for m in data:
            if m.get("poster") in mapping:
                m["poster"] = mapping[m["poster"]]; n += 1
        json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  {f}: rewrote {n} poster paths")

    # rewrite index.html demo posters
    if os.path.exists("index.html"):
        html = open("index.html", encoding="utf-8").read()
        n = 0
        for url, local in mapping.items():
            if url in html:
                html = html.replace(url, local); n += 1
        open("index.html", "w", encoding="utf-8").write(html)
        print(f"  index.html: rewrote {n} poster URLs")

    total = sum(os.path.getsize(os.path.join(OUTDIR, f)) for f in os.listdir(OUTDIR))
    print(f"posters on disk: {len(os.listdir(OUTDIR))} | {total/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
