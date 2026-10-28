#!/usr/bin/env python3
"""fetch_posters.py — give the top N titles a poster, from TMDB.

The site carries 832,677 titles and posters for about 24,000. Fetching all of them is nine hours of
API calls; fetching the ones people actually look at is under an hour. This takes the top N by vote
count — the same ordering the site uses for its rails — and asks TMDB for each one.

A search result is only accepted when the title matches after normalisation AND the year is within
one, because "The Avengers" is three different films and a poster on the wrong one is worse than no
poster at all.

Output is bucketed by the last two digits of the id, like everything else here:

    data/posters/p_<XX>.json.gz    {titleId: "https://image.tmdb.org/t/p/w300/abc.jpg"}

    python3 fetch_posters.py --catalogue data --out data/posters --limit 100000
"""
import argparse, glob, gzip, json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

TMDB = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w300"

def norm(t):
    t = str(t or "").lower().replace("&", "and")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = re.sub(r"\b(the|a|an)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def bucket(key):
    return ("%02d" % (int(key) % 100)) if str(key).isdigit() else "xx"

def catalogue(data_dir):
    out = []
    for p in glob.glob(os.path.join(data_dir, "ix_*.json.gz")):
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        n = len(d.get("t", []))
        for i in range(n):
            out.append((str(d["i"][i]), d["t"][i], d["y"][i], d["v"][i]))
    return out

def tmdb_get(path, key, params):
    q = urllib.parse.urlencode(dict(params, api_key=key))
    url = f"{TMDB}{path}?{q}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if attempt == 2:
                return None
            time.sleep(0.6 * (attempt + 1))
    return None

def one(row, key):
    tid, title, year, votes = row
    if not title:
        return None
    params = {"query": title, "include_adult": "false"}
    if year:
        params["year"] = str(year)
    d = tmdb_get("/search/movie", key, params)
    if not d or not d.get("results"):
        # a second try without the year, which is often wrong in the bulk data
        d = tmdb_get("/search/movie", key, {"query": title, "include_adult": "false"})
        if not d or not d.get("results"):
            return None
    want = norm(title)
    for r in d["results"][:5]:
        if not r.get("poster_path"):
            continue
        if norm(r.get("title")) != want and norm(r.get("original_title")) != want:
            continue
        ry = (r.get("release_date") or "")[:4]
        if year and ry.isdigit() and abs(int(ry) - int(year)) > 1:
            continue
        return (tid, IMG + r["poster_path"])
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogue", default="data")
    ap.add_argument("--out", default="data/posters")
    ap.add_argument("--limit", type=int, default=100000)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()

    key = os.environ.get("TMDB_API_KEY", "").strip()
    if not key:
        print("TMDB_API_KEY is not set"); sys.exit(1)

    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    print("reading the catalogue…")
    cat = catalogue(a.catalogue)
    if not cat:
        print("no catalogue ids"); sys.exit(1)
    print(f"  {len(cat):,} titles")

    # skip anything that already has a poster
    have = set()
    for p in glob.glob(os.path.join(a.out, "p_*.json.gz")):
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                have.update(json.load(f).keys())
        except Exception:
            pass
    if have:
        print(f"  {len(have):,} already have one, skipping those")

    cat.sort(key=lambda r: -(r[3] or 0))          # most watched first
    todo = [r for r in cat if r[0] not in have][:a.limit]
    print(f"  fetching {len(todo):,} posters with {a.workers} workers")

    got = {}
    done = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futures = {ex.submit(one, r, key): r for r in todo}
        for fut in as_completed(futures):
            done += 1
            try:
                res = fut.result()
            except Exception:
                res = None
            if res:
                got[res[0]] = res[1]
            if done % 5000 == 0:
                print(f"    {done:,}/{len(todo):,}  found {len(got):,}  {time.time()-t0:.0f}s")

    print(f"  found {len(got):,} of {len(todo):,} ({len(got)/max(1,len(todo))*100:.0f}%)")

    # merge with what we had, then write the buckets
    by_bucket = {}
    for p in glob.glob(os.path.join(a.out, "p_*.json.gz")):
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                by_bucket[os.path.basename(p)[2:4]] = json.load(f)
        except Exception:
            pass
    for tid, url in got.items():
        by_bucket.setdefault(bucket(tid), {})[tid] = url

    total = 0
    for b, obj in sorted(by_bucket.items()):
        p = os.path.join(a.out, f"p_{b}.json.gz")
        with gzip.open(p, "wt", encoding="utf-8", compresslevel=9) as f:
            json.dump(obj, f, separators=(",", ":"))
        total += os.path.getsize(p)

    man = {"titles": sum(len(v) for v in by_bucket.values()), "files": len(by_bucket),
           "bytes": total, "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(man, open(os.path.join(a.out, "_manifest.json"), "w"), separators=(",", ":"))
    print(f"\nwrote {len(by_bucket)} buckets, {total/1024**2:.1f} MB, {man['titles']:,} posters")
    print(f"took {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
