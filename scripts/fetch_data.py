#!/usr/bin/env python3
"""fetch_data.py — build data/catalog.json from FREE, no-key internet sources.

Sources (no API key, no sign-up):
  * Wikidata Query Service (SPARQL)   -> title, year, genres, description, poster
    https://query.wikidata.org
  * Wikimedia Commons (poster images) -> the browser loads them at runtime

Usage
  python3 scripts/fetch_data.py                       # all languages -> data/catalog.json
  python3 scripts/fetch_data.py --langs Hindi,Tamil   # subset
  python3 scripts/fetch_data.py --langs English --merge
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

WIKIDATA = "https://query.wikidata.org/sparql"
UA = "FilmiSetBot/1.0 (https://github.com/devrajai/filmiset) python-urllib"

# language -> config.  'genres' off = skip the expensive genre join (big languages).
LANGS = {
    "Hindi":     {"qid": "Q1568", "cat": "hindi",          "orig": "Hindi",     "limit": 120, "min_year": 1930, "genres": True},
    "Gujarati":  {"qid": "Q5137", "cat": "gujarati-movie", "orig": "Gujarati",  "limit": 120, "min_year": 1930, "genres": True},
    "Tamil":     {"qid": "Q5885", "cat": "south-dubbed",   "orig": "Tamil",     "limit": 100, "min_year": 1930, "genres": True},
    "Telugu":    {"qid": "Q8097", "cat": "south-dubbed",   "orig": "Telugu",    "limit": 100, "min_year": 1930, "genres": True},
    "Malayalam": {"qid": "Q36236","cat": "south-dubbed",   "orig": "Malayalam", "limit": 100, "min_year": 1930, "genres": True},
    "Kannada":   {"qid": "Q33673","cat": "south-dubbed",   "orig": "Kannada",   "limit": 100, "min_year": 1930, "genres": True},
    "Korean":    {"qid": "Q9176", "cat": "korean-dubbed",  "orig": "Korean",    "limit": 100, "min_year": 1930, "genres": True},
    "English":   {"qid": "Q1860", "cat": "english-dubbed", "orig": "English",   "limit": 80,  "min_year": 2005, "genres": False},
}

GENRE_MOOD = [
    ("comedy", "Comedy"), ("drama", "Emotional"), ("action", "Action"),
    ("thriller", "Thriller"), ("mystery", "Mystery"), ("romance", "Romantic"),
    ("romantic", "Romantic"), ("horror", "Horror"), ("musical", "Feel-Good"),
    ("family", "Family"), ("adventure", "Action"), ("crime", "Thriller"),
    ("fantasy", "Action"), ("war", "Emotional"), ("historical", "Emotional"),
    ("biograph", "Emotional"), ("sport", "Feel-Good"), ("animation", "Family"),
]


def sparql(query, retries=3, timeout=95):
    url = WIKIDATA + "?format=json&query=" + urllib.parse.quote(query)
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    raise last


def query_lang(cfg, limit):
    extra_sel = ' (GROUP_CONCAT(DISTINCT ?gl; separator="|") AS ?genres)' if cfg["genres"] else ''
    extra_opt = ('OPTIONAL { ?film wdt:P136 ?g . ?g rdfs:label ?gl . FILTER(lang(?gl)="en") }'
                 if cfg["genres"] else '')
    return f"""
SELECT ?filmLabel ?year ?image{extra_sel} (SAMPLE(?desc) AS ?description) WHERE {{
  ?film wdt:P31 wd:Q11424 ; wdt:P577 ?date ; wdt:P364 wd:{cfg['qid']} .
  BIND(YEAR(?date) AS ?year)
  FILTER(?year >= {cfg['min_year']} && ?year <= 2026)
  {extra_opt}
  OPTIONAL {{ ?film wdt:P18 ?image }}
  OPTIONAL {{ ?film schema:description ?desc . FILTER(lang(?desc)="en") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?filmLabel ?year ?image
LIMIT {limit}
"""


def norm_genres(raw):
    out = []
    for g in (raw or "").split("|"):
        g = g.strip()
        if not g:
            continue
        g = g.replace(" film", "").replace(" films", "").strip().title()
        if g and g not in out:
            out.append(g)
    return out[:3]


def moods_for(genres):
    moods = []
    for g in genres:
        gl = g.lower()
        for frag, mood in GENRE_MOOD:
            if frag in gl and mood not in moods:
                moods.append(mood)
    return moods[:3]


def poster_url(image):
    if not image:
        return ""
    return image + ("&" if "?" in image else "?") + "width=400"


def fetch_lang(lang, cfg, limit):
    data = sparql(query_lang(cfg, limit))
    out = []
    for r in data["results"]["bindings"]:
        title = r.get("filmLabel", {}).get("value", "").strip()
        if not title or title.startswith("Q"):
            continue
        y = r.get("year", {}).get("value")
        genres = norm_genres(r.get("genres", {}).get("value", ""))
        desc = r.get("description", {}).get("value", "").strip()
        if lang == "Hindi":
            audio = ["Hindi"]
        elif cfg["cat"] == "gujarati-movie":
            audio = [cfg["orig"]]
        else:
            audio = ["Hindi (dub)", cfg["orig"]]
        out.append({
            "t": title, "y": int(y) if y and y.isdigit() else y,
            "cat": cfg["cat"], "type": "Movie",
            "g": genres, "m": moods_for(genres), "a": audio, "o": [],
            "poster": poster_url(r.get("image", {}).get("value", "")),
            "note": desc[:160], "src": "wikidata",
        })
    return out


def dedupe(movies):
    seen, uniq = set(), []
    for m in movies:
        k = (m["t"].lower(), str(m["y"]))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(m)
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/catalog.json")
    ap.add_argument("--langs", default=",".join(LANGS))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()

    existing = []
    if args.merge and os.path.exists(args.out):
        try:
            existing = json.load(open(args.out, encoding="utf-8"))
        except Exception:
            existing = []

    print("Fetching from Wikidata (free, no key)…")
    collected = []
    for lang in [l.strip() for l in args.langs.split(",") if l.strip()]:
        if lang not in LANGS:
            print(f"  ? unknown language {lang}", file=sys.stderr)
            continue
        cfg = LANGS[lang]
        limit = args.limit or cfg["limit"]
        try:
            got = fetch_lang(lang, cfg, limit)
            collected += got
            print(f"  {lang:10s} -> {len(got)} films")
        except Exception as e:
            print(f"  ! {lang}: {type(e).__name__} {e}", file=sys.stderr)

    movies = dedupe(existing + collected)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(movies)} titles -> {args.out}")


if __name__ == "__main__":
    main()
