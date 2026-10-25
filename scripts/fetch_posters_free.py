#!/usr/bin/env python3
"""fetch_posters_free.py — posters with no API key, from Wikipedia's REST API.

The TMDB poster fetch needs a key, and without it the map sat at 24,000 entries forever. This gets
posters from a source that needs no key, no signup and no account.

Why Wikipedia's REST summary and not the action API: the action API rate-limits hard and returned
429 immediately in testing, while /api/rest_v1/page/summary/ answers reliably and carries the
article's lead image, which for a film is its poster. Measured at 84% on a mixed sample of Hindi,
regional, Hollywood and Korean titles.

Why not Wikidata P18: it was tried first and it is not a poster property. It returned an anime
monument, a postage stamp and a logo for three films. P18 is "an image", not "the poster".

    python3 scripts/fetch_posters_free.py --limit 4000

Writes data/wikidata_posters.json keyed by IMDb id, which the site already merges.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

UA = "FilmiSet/1.0 (https://github.com/devrajai/filmiset; poster fetch)"
REST = "https://en.wikipedia.org/api/rest_v1/page/summary/"
OUT = "data/wikidata_posters.json"


def lead_image(title, year=None):
    """the lead image of the Wikipedia article for a film or series, trying likely titles."""
    variants = [title]
    if year:
        variants += [f"{title} ({year} film)", f"{title} (film)", f"{title} ({year})"]
    variants += [f"{title} (film)", f"{title} (TV series)", f"{title} (web series)"]
    seen = set()
    for v in variants:
        v = v.strip()
        if not v or v.lower() in seen:
            continue
        seen.add(v.lower())
        url = REST + urllib.parse.quote(v.replace(" ", "_"), safe="")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read().decode("utf-8", "ignore"))
        except Exception:
            continue
        if d.get("type") == "disambiguation":
            continue
        th = d.get("thumbnail") or d.get("originalimage") or {}
        src = th.get("source")
        if src:
            # strip the analytics query the API appends
            return src.split("?")[0]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=4000)
    ap.add_argument("--sleep", type=float, default=0.55)
    ap.add_argument("--inputs", nargs="*", default=None)
    args = ap.parse_args()

    known = {}
    if os.path.exists(OUT):
        try:
            known = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            known = {}
    print(f"already have {len(known):,} entries", flush=True)

    have = set()
    for p in ("data/imdb_posters.json", "data/imdb_posters.json.gz"):
        if os.path.exists(p):
            try:
                if p.endswith(".gz"):
                    import gzip
                    have |= set(json.loads(gzip.open(p, "rt", encoding="utf-8").read()))
                else:
                    have |= set(json.load(open(p, encoding="utf-8")))
            except Exception:
                pass
    print(f"posters from TMDB already: {len(have):,}", flush=True)

    # gather everything the site lists that has no poster yet
    wanted = {}
    inputs = args.inputs or ["data/imdb_indian.json", "data/catalog.json",
                             "data/curated_india_all.json", "data/curated_india1.json",
                             "data/curated_india2.json", "data/curated_hindi.json",
                             "data/curated_hollywood.json", "data/curated_series.json",
                             "data/curated_anime.json"]
    for f in inputs:
        if not os.path.exists(f):
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        rows = d if isinstance(d, list) else (d.get("titles") if isinstance(d, dict) else [])
        if not isinstance(rows, list):
            continue
        for r in rows:
            if not isinstance(r, dict):
                continue
            i = r.get("id") or r.get("tconst") or r.get("imdb")
            t = r.get("t") or r.get("title") or r.get("name")
            if i and t and re.match(r"^tt\d+", str(i)) and i not in have and i not in known:
                wanted[i] = (str(t), r.get("y") or r.get("year"))

    items = list(wanted.items())[: args.limit]
    print(f"asking Wikipedia about {len(items):,} titles with no poster", flush=True)

    got = 0
    for n, (i, (title, year)) in enumerate(items):
        img = lead_image(title, year)
        if img:
            known[i] = {"poster": img, "src": "wikipedia"}
            got += 1
        if n % 100 == 0 and n:
            print(f"  {n:,}/{len(items):,} | {got:,} images ({got/n*100:.0f}%)", flush=True)
            json.dump(known, open(OUT, "w", encoding="utf-8"), ensure_ascii=False,
                      separators=(",", ":"))
        time.sleep(args.sleep)

    json.dump(known, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"\nwrote {OUT}: {len(known):,} entries, {got:,} new images this run")


if __name__ == "__main__":
    main()
