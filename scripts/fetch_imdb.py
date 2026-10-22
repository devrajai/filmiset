#!/usr/bin/env python3
"""fetch_imdb.py — add IMDb ratings from IMDb's free public datasets (no API key).

Downloads https://datasets.imdbws.com/title.ratings.tsv.gz (~7 MB) and matches it to
our titles by their IMDb id (tconst), which fetch_data.py collects from Wikidata (P345)
and fetch_tmdb.py from TMDB.

Adds:  irt = IMDb rating (0-10)   ivot = IMDb vote count

    python3 scripts/fetch_imdb.py
"""
import argparse, gzip, json, os, sys, urllib.request

URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
TMP = "/tmp/imdb_ratings.tsv.gz"


def load_ratings(path):
    out = {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        f.readline()                       # header
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                out[p[0]] = (p[1], p[2])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", default="data/catalog.json,data/movies.json")
    args = ap.parse_args()

    files = [f.strip() for f in args.files.split(",") if f.strip()]
    loaded = {f: json.load(open(f, encoding="utf-8")) for f in files if os.path.exists(f)}

    need = {m.get("imdb") for data in loaded.values() for m in data
            if m.get("imdb") and not m.get("irt")}
    need.discard("")
    print(f"titles with an IMDb id and no rating yet: {len(need)}")
    if not need:
        print("nothing to do.")
        return

    try:
        if not os.path.exists(TMP):
            print("downloading IMDb ratings dataset…")
            urllib.request.urlretrieve(URL, TMP)
        ratings = load_ratings(TMP)
    except Exception as e:
        print(f"could not load IMDb dataset: {type(e).__name__} {e}", file=sys.stderr)
        return
    print(f"IMDb dataset: {len(ratings)} titles")

    hit = 0
    for data in loaded.values():
        for m in data:
            t = m.get("imdb")
            if t and not m.get("irt") and t in ratings:
                try:
                    m["irt"] = float(ratings[t][0])
                    m["ivot"] = int(ratings[t][1])
                    hit += 1
                except Exception:
                    pass
    for f, data in loaded.items():
        json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"filled IMDb ratings for {hit} titles")


if __name__ == "__main__":
    main()
