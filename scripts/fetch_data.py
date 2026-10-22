#!/usr/bin/env python3
"""fetch_data.py — build data/catalog.json from FREE, no-key internet sources.

Sources (no API key, no sign-up):
  * Wikidata Query Service (SPARQL)  -> title, year, release date, genres, popularity, poster
  * Wikipedia page-images API        -> posters (incl. non-free, pilicense=any)

Usage
  python3 scripts/fetch_data.py                       # everything -> data/catalog.json
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

# non-language film collections
COLLECTIONS = {
    "Anime":     {"cat": "anime", "cats": ["anime", "animation"], "limit": 220, "audio": ["Japanese"],
                  "where": "?film wdt:P31 wd:Q202866 ; wdt:P364 wd:Q5287 ."},
    "Animation": {"cat": "animation", "cats": ["animation"], "limit": 220, "audio": [],
                  "where": "?film wdt:P31 wd:Q202866 ."},
}

# web / TV series (type = Series)
SERIES = {
    "India":   {"cat": "hindi",          "limit": 70, "audio": ["Hindi"],
                "where": "?s wdt:P31/wdt:P279* wd:Q5398426 ; wdt:P495 wd:Q668 ."},
    "Korea":   {"cat": "korean-dubbed",  "limit": 60, "audio": ["Hindi (dub)", "Korean"],
                "where": "?s wdt:P31/wdt:P279* wd:Q5398426 ; wdt:P495 wd:Q884 ."},
    "USA":     {"cat": "english-dubbed", "limit": 60, "audio": ["Hindi (dub)", "English"],
                "where": "?s wdt:P31/wdt:P279* wd:Q5398426 ; wdt:P495 wd:Q30 ."},
    "AnimeTV": {"cat": "anime", "cats": ["anime", "animation"], "limit": 60, "audio": ["Hindi (dub)", "Japanese"],
                "where": "?s wdt:P31/wdt:P279* wd:Q63952888 ."},
}

# film franchises ("part of the series", Wikidata P179)
FRANCHISES = {
    "Marvel Cinematic Universe": "Q642878",
    "DC Extended Universe":      "Q18281265",
    "James Bond":                "Q2484680",
    "Fast & Furious":            "Q1576873",
    "Harry Potter":              "Q216930",
    "Star Wars":                 "Q22092344",
    "Mission: Impossible":       "Q1356213",
    "Jurassic Park":             "Q17862144",
    "Transformers":              "Q2073466",
    "Pirates of the Caribbean":  "Q194318",
    "The Hunger Games":          "Q11885031",
    "The Twilight Saga":         "Q652599",
    "Fifty Shades":              "Q25222455",
    "The Lord of the Rings":     "Q190214",
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
    if cfg.get("genres"):
        return (' (GROUP_CONCAT(DISTINCT ?gl; separator="|") AS ?genres)',
                'OPTIONAL { ?film wdt:P136 ?g . ?g rdfs:label ?gl . FILTER(lang(?gl)="en") }')
    return "", ""


def query_lang(cfg, limit):
    sel, opt = _sel(cfg)
    return f"""
SELECT ?filmLabel ?image ?articleTitle (MIN(?date) AS ?d) (MAX(?sl) AS ?pop){sel} (SAMPLE(?desc) AS ?description) (SAMPLE(?imdb) AS ?imdb) WHERE {{
  ?film wdt:P31 wd:Q11424 ; wdt:P577 ?date ; wdt:P364 wd:{cfg['qid']} .
  BIND(YEAR(?date) AS ?year)
  FILTER(?year >= {cfg['min_year']} && ?year <= 2026)
  OPTIONAL {{ ?film wikibase:sitelinks ?sl }}
  OPTIONAL {{ ?film wdt:P345 ?imdb }}
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
    sel, opt = _sel(cfg)
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
    return f"""
SELECT ?filmLabel ?image ?articleTitle (MIN(?date) AS ?d) (MAX(?sl) AS ?pop){sel} (SAMPLE(?imdb) AS ?imdb) WHERE {{
  ?film wdt:P31 wd:Q11424 ; wdt:P577 ?date ; wdt:P364 wd:{cfg['qid']} .
  FILTER(?date > "{cutoff}"^^xsd:dateTime && ?date < NOW())
  OPTIONAL {{ ?film wikibase:sitelinks ?sl }}
  OPTIONAL {{ ?film wdt:P345 ?imdb }}
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
SELECT ?filmLabel ?date ?image ?articleTitle (MAX(?sl) AS ?pop){sel} (SAMPLE(?imdb) AS ?imdb) WHERE {{
  ?film wdt:P31 wd:Q11424 ; wdt:P577 ?date ; wdt:P364 wd:{cfg['qid']} .
  FILTER(?date > NOW() && ?date < "2029-01-01"^^xsd:dateTime)
  OPTIONAL {{ ?film wikibase:sitelinks ?sl }}
  OPTIONAL {{ ?film wdt:P345 ?imdb }}
  {opt}
  OPTIONAL {{ ?film wdt:P18 ?image }}
  OPTIONAL {{ ?article schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?articleTitle . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?filmLabel ?date ?image ?articleTitle
LIMIT {limit}
"""


def query_collection(cfg, limit):
    return f"""
SELECT ?filmLabel ?image ?articleTitle (MIN(?date) AS ?d) (MAX(?sl) AS ?pop) (GROUP_CONCAT(DISTINCT ?gl; separator="|") AS ?genres) (SAMPLE(?imdb) AS ?imdb) WHERE {{
  {cfg['where']}
  ?film wdt:P577 ?date .
  BIND(YEAR(?date) AS ?year)
  FILTER(?year >= 1950 && ?year <= 2026)
  OPTIONAL {{ ?film wikibase:sitelinks ?sl }}
  OPTIONAL {{ ?film wdt:P345 ?imdb }}
  OPTIONAL {{ ?film wdt:P136 ?g . ?g rdfs:label ?gl . FILTER(lang(?gl)="en") }}
  OPTIONAL {{ ?film wdt:P18 ?image }}
  OPTIONAL {{ ?article schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?articleTitle . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?filmLabel ?image ?articleTitle
LIMIT {limit}
"""


def query_series(cfg, limit):
    return f"""
SELECT ?sLabel ?image ?articleTitle (MIN(?date) AS ?d) (MAX(?sl) AS ?pop) (GROUP_CONCAT(DISTINCT ?gl; separator="|") AS ?genres) (SAMPLE(?imdb) AS ?imdb) WHERE {{
  {cfg['where']}
  OPTIONAL {{ ?s wdt:P571 ?date }}
  OPTIONAL {{ ?s wikibase:sitelinks ?sl }}
  OPTIONAL {{ ?s wdt:P345 ?imdb }}
  OPTIONAL {{ ?s wdt:P136 ?g . ?g rdfs:label ?gl . FILTER(lang(?gl)="en") }}
  OPTIONAL {{ ?s wdt:P18 ?image }}
  OPTIONAL {{ ?article schema:about ?s ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?articleTitle . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?sLabel ?image ?articleTitle
ORDER BY DESC(?pop)
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


def _pop(r):
    v = r.get("pop", {}).get("value")
    return int(v) if v and str(v).isdigit() else 0


def row_to_movie(lang, cfg, title, date, image, genres, desc, wiki, status, pop=0, imdb=""):
    y = int(date[:4]) if date[:4].isdigit() else ""
    m = {
        "t": title, "y": y, "cat": cfg["cat"], "type": "Movie",
        "g": genres, "m": moods_for(genres), "a": audio_for(lang, cfg), "o": [],
        "poster": commons_url(image), "src": "wikidata", "status": status,
        "date": date, "pop": pop, "imdb": (imdb or ""), "_wiki": wiki,
    }
    if desc:
        m["note"] = desc[:160]
    return m


def fetch_lang(lang, cfg, limit):
    out = []
    for r in sparql(query_lang(cfg, limit))["results"]["bindings"]:
        t = r.get("filmLabel", {}).get("value", "").strip()
        if not t or t.startswith("Q"):
            continue
        out.append(row_to_movie(lang, cfg, t, r.get("d", {}).get("value", "")[:10],
                                r.get("image", {}).get("value", ""),
                                norm_genres(r.get("genres", {}).get("value", "")),
                                r.get("description", {}).get("value", "").strip(),
                                r.get("articleTitle", {}).get("value", "").strip(), "released", _pop(r),
                                r.get("imdb", {}).get("value", "")))
    return out


def fetch_recent(lang, cfg, limit, days):
    out = []
    for r in sparql(query_recent(cfg, limit, days))["results"]["bindings"]:
        t = r.get("filmLabel", {}).get("value", "").strip()
        if not t or t.startswith("Q"):
            continue
        out.append(row_to_movie(lang, cfg, t, r.get("d", {}).get("value", "")[:10],
                                r.get("image", {}).get("value", ""),
                                norm_genres(r.get("genres", {}).get("value", "")),
                                "", r.get("articleTitle", {}).get("value", "").strip(), "released", _pop(r),
                                r.get("imdb", {}).get("value", "")))
    return out


def fetch_upcoming(lang, cfg, limit):
    out = []
    for r in sparql(query_upcoming(cfg, limit))["results"]["bindings"]:
        t = r.get("filmLabel", {}).get("value", "").strip()
        if not t or t.startswith("Q"):
            continue
        out.append(row_to_movie(lang, cfg, t, r.get("date", {}).get("value", "")[:10],
                                r.get("image", {}).get("value", ""),
                                norm_genres(r.get("genres", {}).get("value", "")),
                                "", r.get("articleTitle", {}).get("value", "").strip(), "upcoming", _pop(r),
                                r.get("imdb", {}).get("value", "")))
    return out


def fetch_collection(cfg, limit):
    out = []
    for r in sparql(query_collection(cfg, limit))["results"]["bindings"]:
        t = r.get("filmLabel", {}).get("value", "").strip()
        if not t or t.startswith("Q"):
            continue
        date = r.get("d", {}).get("value", "")[:10]
        genres = norm_genres(r.get("genres", {}).get("value", ""))
        if "Animation" not in genres:
            genres = (["Animation"] + genres)[:3]
        out.append({
            "t": t, "y": int(date[:4]) if date[:4].isdigit() else "", "cat": cfg["cat"], "type": "Movie",
            "g": genres, "m": moods_for(genres) or ["Family"], "a": list(cfg.get("audio", [])), "o": [],
            "poster": commons_url(r.get("image", {}).get("value", "")),
            "src": "wikidata", "status": "released", "date": date, "pop": _pop(r),
            "imdb": r.get("imdb", {}).get("value", ""),
            "cats": list(cfg.get("cats", [cfg["cat"]])),
            "_wiki": r.get("articleTitle", {}).get("value", "").strip(),
        })
    return out


def fetch_series(cfg, limit):
    out = []
    for r in sparql(query_series(cfg, limit))["results"]["bindings"]:
        t = r.get("sLabel", {}).get("value", "").strip()
        if not t or t.startswith("Q"):
            continue
        date = r.get("d", {}).get("value", "")[:10]
        genres = norm_genres(r.get("genres", {}).get("value", ""))
        out.append({
            "t": t, "y": int(date[:4]) if date[:4].isdigit() else "", "cat": cfg["cat"], "type": "Series",
            "g": genres, "m": moods_for(genres) or ["Emotional"], "a": list(cfg.get("audio", [])), "o": [],
            "poster": commons_url(r.get("image", {}).get("value", "")),
            "src": "wikidata", "status": "released", "date": date, "pop": _pop(r),
            "imdb": r.get("imdb", {}).get("value", ""),
            "cats": list(cfg.get("cats", [cfg["cat"]])),
            "_wiki": r.get("articleTitle", {}).get("value", "").strip(),
        })
    return out


def query_franchise(qid, limit):
    return f"""
SELECT ?filmLabel ?image ?articleTitle (MIN(?date) AS ?d) (MAX(?sl) AS ?pop) (GROUP_CONCAT(DISTINCT ?gl; separator="|") AS ?genres) (SAMPLE(?imdb) AS ?imdb) WHERE {{
  ?film wdt:P179 wd:{qid} ; wdt:P31 wd:Q11424 ; wdt:P577 ?date .
  OPTIONAL {{ ?film wikibase:sitelinks ?sl }}
  OPTIONAL {{ ?film wdt:P345 ?imdb }}
  OPTIONAL {{ ?film wdt:P136 ?g . ?g rdfs:label ?gl . FILTER(lang(?gl)="en") }}
  OPTIONAL {{ ?film wdt:P18 ?image }}
  OPTIONAL {{ ?article schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?articleTitle . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?filmLabel ?image ?articleTitle
LIMIT {limit}
"""


def fetch_franchise(name, qid, limit=80):
    out = []
    for r in sparql(query_franchise(qid, limit))["results"]["bindings"]:
        t = r.get("filmLabel", {}).get("value", "").strip()
        if not t or t.startswith("Q"):
            continue
        date = r.get("d", {}).get("value", "")[:10]
        genres = norm_genres(r.get("genres", {}).get("value", ""))
        out.append({
            "t": t, "y": int(date[:4]) if date[:4].isdigit() else "",
            "cat": "english-dubbed", "type": "Movie",
            "g": genres, "m": moods_for(genres), "a": ["Hindi (dub)", "English"], "o": [],
            "poster": commons_url(r.get("image", {}).get("value", "")),
            "src": "wikidata", "status": "released", "date": date, "pop": _pop(r),
            "imdb": r.get("imdb", {}).get("value", ""),
            "franchise": name, "_wiki": r.get("articleTitle", {}).get("value", "").strip(),
        })
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
    titles = sorted({m["_wiki"] for m in movies if m.get("_wiki")})
    found = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        url = (WIKI_API + "?action=query&format=json&prop=pageimages&piprop=thumbnail"
               "&pithumbsize=400&pilicense=any&titles=" + urllib.parse.quote("|".join(batch)))
        try:
            q = _get_json(url).get("query", {})
        except Exception as e:
            print(f"  ! pageimages: {type(e).__name__}", file=sys.stderr)
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
    ap.add_argument("--no-series", action="store_true")
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
    for name, cfg in COLLECTIONS.items():
        try:
            got = fetch_collection(cfg, cfg["limit"]); collected += got
            print(f"  {name:10s} -> {len(got)}")
        except Exception as e:
            print(f"  ! {name}: {type(e).__name__}", file=sys.stderr)
    print("Fetching franchises (Marvel, DC, …)…")
    for name, qid in FRANCHISES.items():
        try:
            got = fetch_franchise(name, qid); collected += got
            print(f"  {name:26s} -> {len(got)}")
        except Exception as e:
            print(f"  ! {name}: {type(e).__name__}", file=sys.stderr)
    if not args.no_series:
        for name, cfg in SERIES.items():
            try:
                got = fetch_series(cfg, cfg["limit"]); collected += got
                print(f"  {name:10s} -> {len(got)} series")
            except Exception as e:
                print(f"  ! {name} series: {type(e).__name__}", file=sys.stderr)
    for lang in langs:
        cfg = LANGS[lang]
        try:
            got = fetch_lang(lang, cfg, args.limit or cfg["limit"]); collected += got
            print(f"  {lang:10s} -> {len(got)} films")
        except Exception as e:
            print(f"  ! {lang}: {type(e).__name__}", file=sys.stderr)

    print(f"Fetching recent releases (last {args.recent_days} days)…")
    for lang in langs:
        try:
            got = fetch_recent(lang, LANGS[lang], args.recent_limit, args.recent_days); collected += got
            print(f"  {lang:10s} -> {len(got)} recent")
        except Exception as e:
            print(f"  ! {lang} recent: {type(e).__name__}", file=sys.stderr)

    print("Fetching upcoming films…")
    upcoming = []
    for lang in langs:
        try:
            got = fetch_upcoming(lang, LANGS[lang], args.upcoming_limit); upcoming += got
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
    print(f"wrote {len(movies)} titles -> {args.out}")


if __name__ == "__main__":
    main()
