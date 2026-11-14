#!/usr/bin/env python3
"""fetch_wikidata_new.py — recent Indian films and series from Wikidata.

The gap this fills: TMDB's Indian television coverage is thin, and a show that starts on
JioHotstar today may not appear there at all. IMDb does carry it, and the catalogue rebuild picks
it up — but only if IMDb has indexed it yet, which for a brand-new Indian series can take days.

Wikidata is faster for this. A Wikipedia page is created within a day or two of a notable Indian
release, and every such page is a Wikidata item carrying the IMDb id in property P345. So this asks
Wikidata for Indian films and series with a publication date in the last few months, gets their
IMDb ids, and the site can then match them against the catalogue — anything we do not already have
is genuinely new, and can be shown even before IMDb or TMDB catches up.

Wikidata is CC0 and needs no key. It does require a User-Agent that identifies the caller.

    python3 fetch_wikidata_new.py --out data/wd_new.json.gz --days 120
"""
import argparse, datetime, gzip, json, os, sys, time, urllib.error, urllib.parse, urllib.request

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "FilmiSet/1.0 (https://filmiset.pages.dev; catalogue refresh) python-urllib"

# Q11424 film, Q5398426 television series, Q1259759 miniseries, Q63952888 animated series
TYPES = ("wd:Q11424 wd:Q5398426 wd:Q1259759 wd:Q63952888 "
         "wd:Q202866 wd:Q24856 wd:Q506240 wd:Q1261214")
INDIA = "wd:Q668"


def sparql(query):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    # Wikidata rate-limits the query service and answers 429 when it has had enough. Running the job
    # twice within a minute is enough to trigger it, so a 429 is waited out rather than treated as a
    # failure — a minute or two of sleep is far cheaper than a red run.
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 60 * (attempt + 1)
                print(f"  rate limited, waiting {wait}s…")
                time.sleep(wait)
                continue
            if attempt == 4:
                print(f"  query failed: HTTP {e.code}")
                return None
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            if attempt == 4:
                print(f"  query failed: {str(e)[:140]}")
                return None
            time.sleep(5 * (attempt + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/wd_new.json.gz")
    ap.add_argument("--days", type=int, default=120)
    a = ap.parse_args()

    since = (datetime.date.today() - datetime.timedelta(days=a.days)).isoformat()
    print(f"asking Wikidata for Indian releases since {since}…")

    # Two lighter queries instead of one UNION. Country of origin (P495) and country (P17) are both
    # used for Indian items depending on who created the entry, but asking for both in one query with
    # eight item types pushed past Wikidata's sixty-second limit and came back 504. Each of these runs
    # in a few seconds, and if one fails the other still returns titles.
    base_types = "wd:Q11424 wd:Q5398426 wd:Q1259759 wd:Q63952888 wd:Q202866 wd:Q24856 wd:Q506240 wd:Q1261214"
    variants = [
        ("P495", f"""SELECT ?item ?itemLabel ?date ?imdb ?langLabel ?typeLabel ?sitelinks WHERE {{
  VALUES ?type {{ {base_types} }}
  ?item wdt:P31 ?type .
  ?item wdt:P495 {INDIA} .
  ?item wdt:P577 ?date .
  FILTER(?date >= "{since}T00:00:00Z"^^xsd:dateTime)
  OPTIONAL {{ ?item wdt:P345 ?imdb . }}
  OPTIONAL {{ ?item wdt:P364 ?lang . }}
  OPTIONAL {{ ?item wikibase:sitelinks ?sitelinks . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,hi,ta,te,ml,kn,bn,mr,gu,pa". }}
}}
LIMIT 1500"""),
        # the P17 variant carries only the two commonest types: eight was enough to time out
        ("P17", f"""SELECT ?item ?itemLabel ?date ?imdb ?langLabel ?typeLabel ?sitelinks WHERE {{
  VALUES ?type {{ wd:Q11424 wd:Q5398426 }}
  ?item wdt:P31 ?type .
  ?item wdt:P17 {INDIA} .
  ?item wdt:P577 ?date .
  FILTER(?date >= "{since}T00:00:00Z"^^xsd:dateTime)
  OPTIONAL {{ ?item wdt:P345 ?imdb . }}
  OPTIONAL {{ ?item wdt:P364 ?lang . }}
  OPTIONAL {{ ?item wikibase:sitelinks ?sitelinks . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,hi,ta,te,ml,kn,bn,mr,gu,pa". }}
}}
LIMIT 1500"""),
    ]

    rows = []
    for label, q in variants:
        print(f"  query {label}…")
        d = sparql(q)
        got = ((d or {}).get("results") or {}).get("bindings") or []
        print(f"    {len(got)} rows")
        rows.extend(got)
        time.sleep(8)   # be kind to a free service shared by everyone

    if not rows:
        print("no data from either query"); sys.exit(1)
    print(f"  {len(rows)} rows total")

    seen, out = set(), []
    for r in rows:
        qid = (r.get("item", {}).get("value") or "").rsplit("/", 1)[-1]
        title = (r.get("itemLabel", {}).get("value") or "").strip()
        date = (r.get("date", {}).get("value") or "")[:10]
        imdb = (r.get("imdb", {}).get("value") or "").strip()
        lang = (r.get("langLabel", {}).get("value") or "").strip()
        typ = (r.get("typeLabel", {}).get("value") or "").strip()
        sitelinks = int(r.get("sitelinks", {}).get("value") or 0)

        if not title or not date or qid in seen:
            continue
        # a bare Q-number means no label in any of the languages we asked for
        if title.startswith("Q") and title[1:].isdigit():
            continue
        seen.add(qid)

        out.append({
            "t": title,
            "date": date,
            "y": int(date[:4]) if date[:4].isdigit() else "",
            "imdb": imdb if imdb.startswith("tt") else "",
            "lang": lang,
            "kind": "Series" if ("series" in typ.lower() or "miniseries" in typ.lower()) else "Movie",
            "wd": qid,
            "links": sitelinks,
            "src": "wikidata",
        })

    # most-linked first: a title with more Wikipedia sitelinks is a real release, not a stub
    out.sort(key=lambda x: (-x["links"], x["date"]))
    out = out[:1200]

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    payload = {"updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
               "since": since, "items": out}
    with gzip.open(a.out, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    with_imdb = sum(1 for x in out if x["imdb"])
    print(f"wrote {a.out}  {os.path.getsize(a.out)/1024:.1f} KB")
    print(f"  {len(out)} titles, {with_imdb} with an IMDb id")
    for x in out[:8]:
        print(f"   {x['date']}  {x['kind']:7s} {x['t'][:44]:44s} {x['imdb'] or '—':10s} {x['lang'][:12]}")


if __name__ == "__main__":
    main()
