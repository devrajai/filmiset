#!/usr/bin/env python3
"""fetch_actors.py — actor -> their titles, built from IMDb's own bulk files.

No API, no key, no rate limit: IMDb publishes title.principals (who was in what) and
name.basics (who they are) as plain gzipped TSVs. One run gives the whole graph.

    python3 scripts/fetch_actors.py --limit 400000

Writes data/actors.json:
    {"Aamir Khan": {"id": "nm0451321", "titles": [["tt0169102", "Lagoon: Once Upon a Time in India", 2001, "actor"], ...]}}

and data/title_cast.json (the reverse map, for "who is in this"):
    {"tt0169102": [["Aamir Khan", "actor"], ...]}
"""
import argparse, collections, gzip, json, os, sys, urllib.request

BASICS = "https://datasets.imdbws.com/title.basics.tsv.gz"
PRINCIPALS = "https://datasets.imdbws.com/title.principals.tsv.gz"
NAMES = "https://datasets.imdbws.com/name.basics.tsv.gz"
CACHE = "/tmp/imdb"
# only these jobs count as "acted in" / "directed"
CREDIT = {"actor", "actress", "director", "writer", "producer", "composer"}


def download(url):
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, os.path.basename(url))
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        print(f"  downloading {os.path.basename(url)} …", flush=True)
        urllib.request.urlretrieve(url, dest)
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=400000, help="how many people to keep")
    ap.add_argument("--out-people", default="data/actors.json")
    ap.add_argument("--out-titles", default="data/title_cast.json")
    args = ap.parse_args()

    titles = {}
    with gzip.open(download(BASICS), "rt", encoding="utf-8", errors="ignore") as fh:
        next(fh, None)
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 9 or p[1] in ("tvEpisode", "videoGame"):
                continue
            titles[p[0]] = (p[2], p[5] if p[5] != "\\N" else None, p[1])
    print(f"  titles kept: {len(titles):,}", flush=True)

    people = {}
    with gzip.open(download(NAMES), "rt", encoding="utf-8", errors="ignore") as fh:
        next(fh, None)
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                people[p[0]] = p[1]
    print(f"  people indexed: {len(people):,}", flush=True)

    by_person = collections.defaultdict(list)
    by_title = collections.defaultdict(list)
    with gzip.open(download(PRINCIPALS), "rt", encoding="utf-8", errors="ignore") as fh:
        next(fh, None)
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 6:
                continue
            tconst, _n, nconst, category = p[0], p[1], p[2], p[3]
            if category not in CREDIT:
                continue
            t = titles.get(tconst)
            if not t:
                continue
            name = people.get(nconst)
            if not name:
                continue
            by_person[name].append((tconst, t[0], t[1], category))
            by_title[tconst].append((name, category))

    # keep the people with the most titles — that is what an actor page needs
    ranked = sorted(by_person.items(), key=lambda kv: -len(kv[1]))[: args.limit]
    out_people = {}
    for name, credits in ranked:
        # de-duplicate, keep the newest first
        seen = set(); clean = []
        for c in sorted(credits, key=lambda x: (x[2] or "0"), reverse=True):
            if c[0] in seen:
                continue
            seen.add(c[0]); clean.append(c)
        out_people[name] = {"titles": clean[:200]}
    json.dump(out_people, open(args.out_people, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  wrote {args.out_people}: {len(out_people):,} people")

    keep = {c[0] for credits in out_people.values() for c in credits["titles"]}
    out_titles = {k: v for k, v in by_title.items() if k in keep}
    json.dump(out_titles, open(args.out_titles, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  wrote {args.out_titles}: {len(out_titles):,} titles with a cast list")


if __name__ == "__main__":
    main()
