#!/usr/bin/env python3
"""fetch_imdb_cast.py — cast and director for every title, from IMDb's own bulk files.

This replaces the per-title TMDB lookups for cast/director. IMDb publishes the same information
as plain files, so there is no API, no key and no rate limit:

    title.crew.tsv.gz        tconst -> directors[], writers[]      (~2.5M rows)
    title.principals.tsv.gz  tconst -> the billed people, in order  (~50M rows)
    name.basics.tsv.gz       nconst -> the person's name            (~12M rows)

Output (only for the titles we care about, so the file stays small):

    data/imdb_cast.json.gz   { "tt0111161": {"d": "Frank Darabont",
                                             "c": ["Tim Robbins", "Morgan Freeman", ...]} }

One pass over the files covers every title at once — the whole catalogue in a single run rather
than tens of thousands of API calls.

    python3 scripts/fetch_imdb_cast.py --limit 300000
"""
import argparse, csv, gzip, json, os, sys, urllib.request

BASE = "https://datasets.imdbws.com"
OUT = "data/imdb_cast.json.gz"
SRC = "data/imdb_all.json.gz"
CAST_LIMIT = 6          # how many cast names to keep per title


def download(name):
    if os.path.exists(name):
        return name
    print(f"  downloading {name} …")
    req = urllib.request.Request(f"{BASE}/{name}", headers={"User-Agent": "FilmiSet/1.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(name, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    print(f"  {name}: {os.path.getsize(name) / 1048576:.0f} MB")
    return name


def wanted_titles(limit):
    ids = []
    try:
        import ijson
        with gzip.open(SRC, "rt", encoding="utf-8") as f:
            for i, item in enumerate(ijson.items(f, "item")):
                if i >= limit:
                    break
                if item.get("id"):
                    ids.append(item["id"])
    except Exception as e:
        print(f"could not read {SRC}: {type(e).__name__} {e}", file=sys.stderr)
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300000, help="how many of the most-voted titles to cover")
    args = ap.parse_args()

    ids = wanted_titles(args.limit)
    if not ids:
        print("no titles to look up — is data/imdb_all.json.gz present?")
        return
    want = set(ids)
    print(f"covering {len(want):,} titles")

    # --- directors ---
    directors = {}
    f = download("title.crew.tsv.gz")
    with gzip.open(f, "rt", encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(r, None)
        for row in r:
            if len(row) >= 2 and row[0] in want:
                d = [x for x in row[1].split(",") if x and x != "\\N"]
                if d:
                    directors[row[0]] = d
    print(f"  directors found for {len(directors):,} titles")

    # --- people's names (only the ones we will actually print) ---
    needed = set()
    for d in directors.values():
        needed.update(d)
    cast_rows = {}
    f = download("title.principals.tsv.gz")
    with gzip.open(f, "rt", encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(r, None)
        for row in r:
            if len(row) < 6 or row[0] not in want:
                continue
            cat, nconst = row[3], row[2]
            if cat in ("actor", "actress", "self") and nconst != "\\N":
                lst = cast_rows.setdefault(row[0], [])
                if len(lst) < CAST_LIMIT:
                    lst.append(nconst)
                    needed.add(nconst)
    print(f"  billed cast found for {len(cast_rows):,} titles")

    names = {}
    f = download("name.basics.tsv.gz")
    with gzip.open(f, "rt", encoding="utf-8", newline="") as fh:
        r = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(r, None)
        for row in r:
            if len(row) >= 2 and row[0] in needed:
                names[row[0]] = row[1]
                if len(names) >= len(needed):
                    break
    print(f"  resolved {len(names):,} names")

    out = {}
    for t in want:
        d = [names.get(n, "") for n in directors.get(t, [])]
        d = [x for x in d if x]
        c = [names.get(n, "") for n in cast_rows.get(t, [])]
        c = [x for x in c if x]
        if d or c:
            out[t] = {}
            if d:
                out[t]["d"] = ", ".join(d[:2])
            if c:
                out[t]["c"] = c[:CAST_LIMIT]

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print(f"wrote {OUT}: {len(out):,} titles with cast or director "
          f"({os.path.getsize(OUT) / 1048576:.1f} MB)")


if __name__ == "__main__":
    main()
