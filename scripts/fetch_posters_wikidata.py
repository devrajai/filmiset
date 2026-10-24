#!/usr/bin/env python3
"""fetch_posters_wikidata.py — posters and one-line summaries without TMDB.

Wikidata is the best free alternative for images: the data is CC0 (no attribution required,
no key, no rate limit beyond being polite), and every film that has a Wikipedia article usually
has a P18 image and a short description. Coverage is thinner than TMDB for Indian cinema, so
this is a *second* source that fills gaps — run it after the TMDB pass, not instead of it.

    python3 scripts/fetch_posters_wikidata.py --limit 20000

Writes data/wikidata_posters.json:
    {"imdb": "tt0169102", "poster": "https://upload.wikimedia.org/…", "desc": "1999 film by Ashutosh Gowariker"}
keyed by IMDb id, so the site can merge it with imdb_posters.json.
"""
import argparse, json, os, time, urllib.parse, urllib.request

SPARQL = "https://query.wikidata.org/sparql"
OUT = "data/wikidata_posters.json"
UA = "FilmiSet/1.0 (https://github.com/devrajai/filmiset) python-urllib"


def sparql(query):
    url = SPARQL + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20000)
    ap.add_argument("--batch", type=int, default=300, help="IMDb ids per query — Wikidata likes small batches")
    ap.add_argument("--ids", default="data/poster_ids.json", help="imdb ids still missing a poster")
    args = ap.parse_args()

    known = {}
    if os.path.exists(OUT):
        try: known = json.load(open(OUT, encoding="utf-8"))
        except Exception: known = {}

    ids = []
    if os.path.exists(args.ids):
        try:
            raw = json.load(open(args.ids, encoding="utf-8"))
            ids = list(raw)[: args.limit] if isinstance(raw, (list, dict)) else []
        except Exception:
            ids = []
    ids = [i for i in ids if i not in known]
    print(f"already have {len(known):,} | asking about {len(ids):,}")
    if not ids:
        print("nothing to do — pass --ids with the ids you still need")
        return

    got = 0
    for i in range(0, len(ids), args.batch):
        chunk = ids[i:i + args.batch]
        values = " ".join('"%s"' % c for c in chunk)
        q = f"""SELECT ?imdb ?image ?desc WHERE {{
  VALUES ?imdb {{ {values} }}
  ?film wdt:P345 ?imdb .
  OPTIONAL {{ ?film wdt:P18 ?image . }}
  OPTIONAL {{ ?film schema:description ?desc . FILTER(LANG(?desc) = "en") }}
}}"""
        try:
            d = sparql(q)
        except Exception as e:
            print(f"  batch {i//args.batch}: {type(e).__name__} — backing off")
            time.sleep(5); continue
        for b in d.get("results", {}).get("bindings", []):
            imdb = b.get("imdb", {}).get("value")
            if not imdb:
                continue
            rec = known.get(imdb, {})
            if b.get("image"): rec["poster"] = b["image"]["value"]
            if b.get("desc"):  rec["desc"] = b["desc"]["value"]
            if rec and imdb not in known: got += 1
            if rec: known[imdb] = rec
        print(f"  {min(i+args.batch, len(ids)):,}/{len(ids):,} asked, {len(known):,} with data", flush=True)
        json.dump(known, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        time.sleep(1)                       # be a polite guest

    json.dump(known, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    with_poster = sum(1 for v in known.values() if v.get("poster"))
    print(f"wrote {OUT}: {len(known):,} titles, {with_poster:,} with an image")


if __name__ == "__main__":
    main()
