#!/usr/bin/env python3
"""sheet_to_json.py — convert the FilmiSet Google Sheet (Catalog tab) into data/movies.json.

Two ways to feed it:

  1) Published CSV URL (easiest, no credentials):
     In Google Sheets:  File -> Share -> Publish to web -> pick the "Catalog" sheet -> CSV
     Copy the link, then:
         python3 scripts/sheet_to_json.py --url "https://docs.google.com/spreadsheets/d/e/..../pub"

  2) A downloaded CSV file (File -> Download -> CSV, then upload just the Catalog tab):
         python3 scripts/sheet_to_json.py --csv ~/Downloads/FilmiSet.csv

Output: data/movies.json  (overwrite with --out)
"""
import argparse, csv, json, os, sys, urllib.request

# Sheet category label -> site category key
CATMAP = {
    "gujarati movie": "gujarati-movie",
    "gujarati natak": "gujarati-natak",
    "hindi": "hindi",
    "south - hindi dubbed": "south-dubbed",
    "english - hindi dubbed": "english-dubbed",
    "korean - hindi dubbed": "korean-dubbed",
}


def split_multi(s):
    return [x.strip() for x in str(s or "").split(",") if x.strip()]


def to_int(v):
    v = str(v or "").strip()
    return int(v) if v.isdigit() else v


def rows_to_movies(rows):
    """rows: list of dicts keyed by header name (from csv.DictReader)."""
    out = []
    for r in rows:
        title = (r.get("Title") or "").strip()
        if not title:
            continue
        cat = (r.get("Category") or "").strip().lower()
        out.append({
            "t": title,
            "y": to_int(r.get("Year")),
            "cat": CATMAP.get(cat, "hindi"),
            "type": (r.get("Type") or "Movie").strip(),
            "g": split_multi(r.get("Genres")),
            "m": split_multi(r.get("Mood Tags")),
            "a": split_multi(r.get("Available Audio")),
            "o": split_multi(r.get("OTT Platforms")),
            "note": (r.get("Notes") or "").strip(),
        })
    return out


def read_rows(url=None, csv_path=None):
    if url:
        with urllib.request.urlopen(url, timeout=30) as resp:
            text = resp.read().decode("utf-8-sig")
        return list(csv.DictReader(text.splitlines()))
    if csv_path:
        with open(os.path.expanduser(csv_path), newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    sys.exit("error: pass --url or --csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="published Google Sheets CSV URL")
    ap.add_argument("--csv", help="path to a downloaded CSV")
    ap.add_argument("--out", default="data/movies.json")
    args = ap.parse_args()

    movies = rows_to_movies(read_rows(args.url, args.csv))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(movies)} titles -> {args.out}")


if __name__ == "__main__":
    main()
