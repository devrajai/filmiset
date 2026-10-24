#!/usr/bin/env python3
"""build_filmography.py — the actor graph the whole feature set sits on.

Everything here comes from IMDb's own bulk files: no API, no key, no rate limit, and nothing
that expires when a key is switched off. It replaces the TMDB version for our purposes, because
the site must keep working after TMDB is disconnected.

    python3 scripts/build_filmography.py --top 8000

Writes (all small enough to ship):
    data/filmography.json   actor -> their titles, with year, genre, rating, votes
    data/co_stars.json      the pairs who have worked together most often
    data/actor_index.json   just names and ids, for the search box

Design notes:
  * Only the top N actors by number of credits are kept. A complete graph is millions of edges
    and the browser cannot hold it; 8,000 covers every name anyone will actually type.
  * Episodes and video games are excluded from the graph — an actor page full of single episodes
    is noise.
  * Anything derived from box office is labelled an estimate, always. TMDB carries budget and
    revenue for a minority of Indian films, and a confident-looking wrong number is worse than
    an honest gap.
"""
import argparse, collections, gzip, json, os, sys, urllib.request

BASICS     = "https://datasets.imdbws.com/title.basics.tsv.gz"
RATINGS    = "https://datasets.imdbws.com/title.ratings.tsv.gz"
NAMES      = "https://datasets.imdbws.com/name.basics.tsv.gz"
PRINCIPALS = "https://datasets.imdbws.com/title.principals.tsv.gz"
CACHE      = "/tmp/imdb"
CREDIT     = {"actor", "actress", "director"}
KEEP_TYPES = {"movie", "tvSeries", "tvMiniSeries", "tvMovie", "short", "tvShort"}


def download(url):
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, os.path.basename(url))
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        print(f"  downloading {os.path.basename(url)} …", flush=True)
        urllib.request.urlretrieve(url, dest)
    return dest


def rows(path, cols):
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as fh:
        head = next(fh).rstrip("\n").split("\t")
        idx = [head.index(c) for c in cols]
        for line in fh:
            p = line.rstrip("\n").split("\t")
            try: yield tuple(None if p[i] == "\\N" else p[i] for i in idx)
            except IndexError: continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=8000, help="how many actors to keep")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    print("1/4 titles")
    titles = {}
    for tconst, ttype, primary, year, runtime, genres in rows(
            download(BASICS), ["tconst","titleType","primaryTitle","startYear","runtimeMinutes","genres"]):
        if ttype not in KEEP_TYPES: continue
        titles[tconst] = {"t": primary, "y": int(year) if year and year.isdigit() else None,
                          "rt": int(runtime) if runtime and runtime.isdigit() else None,
                          "g": (genres or "").split(",") if genres else [], "k": ttype}
    print(f"   kept {len(titles):,} titles")

    print("2/4 ratings")
    ratings = {}
    for tconst, rating, votes in rows(download(RATINGS), ["tconst","averageRating","numVotes"]):
        ratings[tconst] = (float(rating), int(votes))
    print(f"   {len(ratings):,} rated")

    print("3/4 people")
    people = {}
    for nconst, name in rows(download(NAMES), ["nconst","primaryName"]):
        people[nconst] = name
    print(f"   {len(people):,} people")

    print("4/4 credits — this is the long one")
    by_person = collections.defaultdict(list)
    by_title  = collections.defaultdict(list)
    for tconst, nconst, category in rows(download(PRINCIPALS), ["tconst","nconst","category"]):
        if category not in CREDIT: continue
        t = titles.get(tconst)
        if not t: continue
        n = people.get(nconst)
        if not n: continue
        by_person[n].append((tconst, category))
        by_title[tconst].append((n, category))

    ranked = sorted(by_person.items(), key=lambda kv: -len(kv[1]))[: args.top]
    print(f"   kept the top {len(ranked):,} people by credits")

    filmography = {}
    for name, credits in ranked:
        seen, films = set(), []
        for tconst, category in credits:
            if tconst in seen: continue
            seen.add(tconst)
            t = titles[tconst]
            r = ratings.get(tconst)
            films.append({"id": tconst, "t": t["t"], "y": t["y"], "rt": t["rt"],
                          "g": t["g"][:3], "k": t["k"], "c": category,
                          "irt": r[0] if r else None, "ivot": r[1] if r else None})
        films.sort(key=lambda f: (f["y"] or 0), reverse=True)
        rated = [f["irt"] for f in films if f["irt"]]
        years = [f["y"] for f in films if f["y"]]
        # the range meter: how many different genres, and how many kinds of role
        genres = collections.Counter(g for f in films for g in f["g"])
        kinds  = collections.Counter(f["c"] for f in films)
        best   = max(films, key=lambda f: (f["irt"] or 0), default=None)
        # underrated: rated well but hardly seen
        under  = sorted([f for f in films if f["irt"] and (f["ivot"] or 0) < 5000 and f["irt"] >= 7.0],
                        key=lambda f: -(f["irt"] or 0))[:3]
        filmography[name] = {
            "n": len(films), "first": min(years) if years else None, "last": max(years) if years else None,
            "avg": round(sum(rated)/len(rated), 1) if rated else None,
            "genres": dict(genres.most_common(8)), "kinds": dict(kinds),
            "range": len(genres), "best": best["t"] if best else None,
            "under": [f["t"] for f in under],
            "films": films[:200],
        }

    print("co-stars")
    pairs = collections.Counter()
    for tconst, cast in by_title.items():
        names = [n for n, _ in cast if n in filmography]
        for i in range(len(names)):
            for j in range(i+1, len(names)):
                pairs[tuple(sorted((names[i], names[j])))] += 1
    co = [{"a": a, "b": b, "n": n} for (a, b), n in pairs.most_common(4000) if n >= 2]
    print(f"   {len(co):,} pairs who worked together at least twice")

    os.makedirs(args.out, exist_ok=True)
    def dump(name, obj):
        p = os.path.join(args.out, name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
        print(f"   wrote {p} ({os.path.getsize(p)/1e6:.1f} MB)")

    dump("filmography.json", filmography)
    dump("co_stars.json", co)
    dump("actor_index.json", sorted(filmography.keys()))


if __name__ == "__main__":
    main()
