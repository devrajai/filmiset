#!/usr/bin/env python3
"""fetch_data.py — build data/catalog.json from FREE, no-key internet sources.

Sources (no API key, no sign-up):
  * Wikidata Query Service (SPARQL)      -> title, year, release date, genres, description
    https://query.wikidata.org
  * Wikipedia page-images API            -> posters (incl. non-free, pilicense=any)
    https://en.wikipedia.org/w/api.php
  * Wikimedia Commons (Wikidata P18)     -> fallback poster when Wikipedia has none

Usage
  python3 scripts/fetch_data.py                       # all languages -> data/catalog.json
  python3 scripts/fetch_data.py --langs Hindi,Tamil
  python3 scripts/fetch_data.py --no-posters
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta

WIKIDATA = "https://query.wikidata.org/sparql"
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = "FilmiSetBot/1.0 (https://github.com/devrajai/filmiset) python-urllib"

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


def _get_json(url, retries=3, timeout=60):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def sparql(query):
    return _get_json(WIKIDATA + "?format=json&query=" + urllib.parse.quote(query), timeout=95)


def _sel(cfg):
    """genre SELECT clause + OPTIONAL clause (skipped for very large languages)."""
    if cfg["genres"]:
        return (' (GROUP_CONCAT(DISTINCT ?gl; separator="|") AS ?genres)',
                'OPTIONAL { ?film wdt:P136 ?g . ?g rdfs:label ?gl . FILTER(lang(?gl)="en") }')
    return "", ""


def query_lang(cfg, limit):
    sel, opt = _sel(cfg)
    return f"""
SELECT ?filmLabel ?image ?articleTitle (MIN(?date) AS ?d){sel} (SAMPLE(?desc) AS ?description) WHERE {{
  ?film wdt:P31 wd:Q11424 ; wdt:P577 ?date ; wdt:P364 wd:{cfg['qid']} .
  BIND(YEAR(?date) AS ?year)
  FILTER(?year >= {cfg['min_year']} && ?year <= 2026)
  {opt}
  OPTIONAL {{ ?film wdt:P18 ?image }}
  OPTIONAL {{ ?film schema:description ?desc . FILTER(lang(?desc)="en") }}
  OPTIONAL {{ ?article schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?articleTitle . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?filmLabel ?image ?articleTitle
LIMIT {limit}
"""


def query_recent(cfg, limit, days):
    """Films released in the last `days` days — guarantees fresh content."""
    sel, opt = _sel(cfg)
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
    return f"""
SELECT ?filmLabel ?image ?articleTitle (MIN(?date) AS ?d){sel} WHERE {{
  ?film wdt:P31 wd:Q11424 ; wdt:P577 ?date ; wdt:P364 wd:{cfg['qid']} .
  FILTER(?date > "{cutoff}"^^xsd:dateTime && ?date < NOW())
  {opt}
  OPTIONAL {{ ?film wdt:P18 ?image }}
  OPTIONAL {{ ?article schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?articleTitle . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?filmLabel ?image ?articleTitle
LIMIT {limit}
"""


def query_upcoming(cfg, limit):
    sel, opt = _sel(cfg)
    return f"""
SELECT ?filmLabel ?date ?image ?articleTitle{sel} WHERE {{
  ?film wdt:P31 wd:Q11424 ; wdt:P577 ?date ; wdt:P364 wd:{cfg['qid']} .
  FILTER(?date > NOW() && ?date < "2029-01-01"^^xsd:dateTime)
  {opt}
  OPTIONAL {{ ?film wdt:P18 ?image }}
  OPTIONAL {{ ?article schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?articleTitle . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?filmLabel ?date ?image ?articleTitle
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


def commons_url(image):
    if not image:
        return ""
    return image + ("&" if "?" in image else "?") + "width=400"


def audio_for(lang, cfg):
    if lang == "Hindi":
        return ["Hindi"]
    if cfg["cat"] == "gujarati-movie":
        return [cfg["orig"]]
    return ["Hindi (dub)", cfg["orig"]]


def row_to_movie(lang, cfg, title, date, image, genres, desc, wiki, status):
    y = int(date[:4]) if date[:4].isdigit() else ""
    m = {
        "t": title, "y": y, "cat": cfg["cat"], "type": "Movie",
        "g": genres, "m": moods_for(genres), "a": audio_for(lang, cfg), "o": [],
        "poster": commons_url(image), "src": "wikidata", "status": status,
        "date": date, "_wiki": wiki,
    }
    if desc:
        m["note"] = desc[:160]
    return m


def fetch_lang(lang, cfg, limit):
    data = sparql(query_lang(cfg, limit))
    out = []
    for r in data["results"]["bindings"]:
        title = r.get("filmLabel", {}).get("value", "").strip()
        if not title or title.startswith("Q"):
            continue
        out.append(row_to_movie(
            lang, cfg, title,
            r.get("d", {}).get("value", "")[:10],
            r.get("image", {}).get("value", ""),
            norm_genres(r.get("genres", {}).get("value", "")),
            r.get("description", {}).get("value", "").strip(),
            r.get("articleTitle", {}).get("value", "").strip(), "released"))
    return out


def fetch_recent(lang, cfg, limit, days):
    data = sparql(query_recent(cfg, limit, days))
    out = []
    for r in data["results"]["bindings"]:
        title = r.get("filmLabel", {}).get("value", "").strip()
        if not title or title.startswith("Q"):
            continue
        out.append(row_to_movie(
            lang, cfg, title,
            r.get("d", {}).get("value", "")[:10],
            r.get("image", {}).get("value", ""),
            norm_genres(r.get("genres", {}).get("value", "")),
            "", r.get("articleTitle", {}).get("value", "").strip(), "released"))
    return out


def fetch_upcoming(lang, cfg, limit):
    data = sparql(query_upcoming(cfg, limit))
    out = []
    for r in data["results"]["bindings"]:
        title = r.get("filmLabel", {}).get("value", "").strip()
        if not title or title.startswith("Q"):
            continue
        out.append(row_to_movie(
            lang, cfg, title,
            r.get("date", {}).get("value", "")[:10],
            r.get("image", {}).get("value", ""),
            norm_genres(r.get("genres", {}).get("value", "")),
            "", r.get("articleTitle", {}).get("value", "").strip(), "upcoming"))
    return out


def dedupe(movies):
    seen, uniq = set(), []
    for m in movies:
        key = (m["t"].lower(), "up" if m.get("status") == "upcoming" else str(m["y"]))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(m)
    return uniq


def attach_posters(movies):
    """Fill 'poster' from the Wikipedia page-image (works for non-free posters too)."""
    titles = sorted({m["_wiki"] for m in movies if m.get("_wiki")})
    found = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        url = (WIKI_API + "?action=query&format=json&prop=pageimages&piprop=thumbnail"
               "&pithumbsize=400&pilicense=any&titles=" + urllib.parse.quote("|".join(batch)))
        try:
            q = _get_json(url).get("query", {})
        except Exception as e:
            print(f"  ! pageimages batch: {type(e).__name__}", file=sys.stderr)
            continue
        norm = {n["from"]: n["to"] for n in q.get("normalized", [])}
        redir = {r["from"]: r["to"] for r in q.get("redirects", [])}
        by_title = {}
        for p in q.get("pages", {}).values():
            thumb = (p.get("thumbnail") or {}).get("source")
            if thumb:
                by_title[p["title"]] = thumb.split("?")[0]
        for t in batch:
            key = redir.get(norm.get(t, t), norm.get(t, t))
            if key in by_title:
                found[t] = by_title[key]
    hit = 0
    for m in movies:
        w = m.get("_wiki")
        if w and w in found:
            m["poster"] = found[w]
            hit += 1
    print(f"  posters: {hit}/{len(movies)} from Wikipedia")
    return movies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/catalog.json")
    ap.add_argument("--langs", default=",".join(LANGS))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--no-posters", action="store_true")
    ap.add_argument("--recent-days", type=int, default=150)
    ap.add_argument("--recent-limit", type=int, default=40)
    ap.add_argument("--upcoming-limit", type=int, default=30)
    args = ap.parse_args()

    existing = []
    if args.merge and os.path.exists(args.out):
        try:
            existing = json.load(open(args.out, encoding="utf-8"))
        except Exception:
            existing = []

    langs = [l.strip() for l in args.langs.split(",") if l.strip() and l.strip() in LANGS]

    print("Fetching from Wikidata (free, no key)…")
    collected = []
    for lang in langs:
        cfg = LANGS[lang]
        try:
            got = fetch_lang(lang, cfg, args.limit or cfg["limit"])
            collected += got
            print(f"  {lang:10s} -> {len(got)} films")
        except Exception as e:
            print(f"  ! {lang}: {type(e).__name__} {e}", file=sys.stderr)

    print(f"Fetching recent releases (last {args.recent_days} days)…")
    for lang in langs:
        try:
            got = fetch_recent(lang, LANGS[lang], args.recent_limit, args.recent_days)
            collected += got
            print(f"  {lang:10s} -> {len(got)} recent")
        except Exception as e:
            print(f"  ! {lang} recent: {type(e).__name__}", file=sys.stderr)

    print("Fetching upcoming films…")
    upcoming = []
    for lang in langs:
        try:
            got = fetch_upcoming(lang, LANGS[lang], args.upcoming_limit)
            upcoming += got
            print(f"  {lang:10s} -> {len(got)} upcoming")
        except Exception as e:
            print(f"  ! {lang} upcoming: {type(e).__name__}", file=sys.stderr)
    upcoming.sort(key=lambda m: m.get("date", "9999"))
    collected += upcoming

    movies = dedupe(existing + collected)
    if not args.no_posters:
        print("Fetching posters from Wikipedia…")
        attach_posters(movies)
    for m in movies:
        m.pop("_wiki", None)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=1)

    dated = sum(1 for m in movies if m.get("date"))
    print(f"wrote {len(movies)} titles -> {args.out}  ({dated} with release dates)")


if __name__ == "__main__":
    main()
