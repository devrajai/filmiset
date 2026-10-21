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
import argparse, csv, json, os, re, sys, urllib.parse, urllib.request

UA = "FilmiSetBot/1.0 (https://github.com/devrajai/filmiset)"

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
            "occ": split_multi(r.get("Occasion Tags")),
            "poster": "",
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


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def lookup_poster(title):
    """Best-effort poster from Wikipedia (free, no key). Returns a URL or None."""
    url = ("https://en.wikipedia.org/w/api.php"
           "&generator=search&gsrsearch=" + urllib.parse.quote(title + " film") + "&gsrlimit=1"
           "&prop=pageimages&piprop=thumbnail&pithumbsize=400&pilicense=any")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            q = (json.loads(r.read().decode("utf-8")).get("query") or {})
    except Exception:
        return None
    for p in q.get("pages", {}).values():
        thumb = (p.get("thumbnail") or {}).get("source")
        if thumb and _norm(title) in _norm(p.get("title")):
            return thumb.split("?")[0]
    return None


def enrich_posters(movies):
    n = 0
    for m in movies:
        if m.get("poster"):
            continue
        url = lookup_poster(m["t"])
        if url:
            m["poster"] = url
            n += 1
    print(f"  posters: +{n} from Wikipedia")
    return movies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="published Google Sheets CSV URL")
    ap.add_argument("--csv", help="path to a downloaded CSV")
    ap.add_argument("--out", default="data/movies.json")
    ap.add_argument("--no-posters", action="store_true", help="skip the Wikipedia poster lookup")
    args = ap.parse_args()

    movies = rows_to_movies(read_rows(args.url, args.csv))
    if not args.no_posters:
        print("Fetching posters from Wikipedia…")
        enrich_posters(movies)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(movies)} titles -> {args.out}")


if __name__ == "__main__":
    main()
