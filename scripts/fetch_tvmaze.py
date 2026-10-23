#!/usr/bin/env python3
"""fetch_tvmaze.py — episode, season and network data for every curated series.

TVmaze runs an open REST API with **no key and no signup**, which makes it a good free source
for the TV side of the catalogue: how many seasons and episodes a show has, which network or
streamer carried it, when it premiered, and its status (running / ended).

    python3 scripts/fetch_tvmaze.py
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

API = "https://api.tvmaze.com"
OUT = "data/tvmaze.json"
TARGETS = ["curated_series.json", "curated_hollywood_series.json",
           "curated_netflix_series.json", "curated_prime.json", "curated_hotstar.json"]


def get(path, params=None):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "FilmiSet/1.0 (github.com/devrajai/filmiset)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def norm(t):
    t = str(t or "").lower().replace("&", "and")
    t = re.sub(r"\b(the|a|an)\b", " ", re.sub(r"[^a-z0-9]+", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def strip(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def lookup(title):
    try:
        show = get("/singlesearch/shows", {"q": title})
    except Exception:
        return None
    if not show or not show.get("id"):
        return None
    sid = show["id"]
    info = {
        "net": (show.get("network") or {}).get("name") or (show.get("webChannel") or {}).get("name") or "",
        "premiered": show.get("premiered") or "",
        "status": show.get("status") or "",
        "genres": (show.get("genres") or [])[:3],
        "summary": strip(show.get("summary"))[:300],
        "tvmaze": sid,
    }
    try:
        eps = get(f"/shows/{sid}/episodes")
        if isinstance(eps, list) and eps:
            seasons = sorted({e.get("season") for e in eps if e.get("season")})
            info["seasons"] = len(seasons)
            info["eps"] = len(eps)
    except Exception:
        pass
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=0.25)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

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
                if r.get("t") and (r.get("type") == "Series" or "series" in f):
                    todo.append(r["t"])
        except Exception:
            continue

    print(f"series to check: {len(todo):,} (already known: {len(out):,})")
    n = 0
    for t in todo:
        k = norm(t)
        if not k or k in out:
            continue
        if args.limit and n >= args.limit:
            break
        out[k] = lookup(t) or {}
        n += 1
        if n % 100 == 0:
            print(f"  {n:,} looked up")
            json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        time.sleep(args.delay)

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"wrote {OUT}: {len(out):,} series, {sum(1 for v in out.values() if v.get('eps')):,} with episode counts")


if __name__ == "__main__":
    main()
