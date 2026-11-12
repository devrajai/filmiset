#!/usr/bin/env python3
"""fetch_calendar.py — a month-by-month release calendar, by country, for cinema and for streaming.

TMDB carries release dates per country with a type: 2 and 3 are theatrical, 4 is digital, 5 physical,
6 TV. That is enough to build a real calendar rather than a guess — each row lands in a month because
TMDB says it releases in that month in that country, not because it was popular that week.

For India's digital releases the platform is looked up per title through /movie/{id}/watch/providers,
because "on which OTT" is the question this calendar exists to answer. That is one extra call each,
so it is done only for India and only for digital entries.

    python3 fetch_calendar.py --out data/calendar.json.gz --months 4
"""
import argparse, datetime, gzip, json, os, sys, time, urllib.parse, urllib.request

TMDB = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w300"

COUNTRIES = [("IN", "India"), ("US", "United States"), ("GB", "United Kingdom"),
             ("AE", "UAE"), ("AU", "Australia"), ("CA", "Canada"), ("SG", "Singapore")]

# release_type: 2 limited theatrical, 3 theatrical, 4 digital, 5 physical, 6 TV
KINDS = [("theatre", "2|3"), ("digital", "4")]


def get(path, key, **params):
    q = urllib.parse.urlencode(dict(params, api_key=key, language="en-US"))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f"{TMDB}{path}?{q}", timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if attempt == 2:
                return None
            time.sleep(0.7 * (attempt + 1))
    return None


def shape(r, kind):
    d = r.get("release_date") or r.get("first_air_date") or ""
    poster = r.get("poster_path")
    return {
        "t": r.get("title") or r.get("name") or "",
        "date": d,
        "y": int(d[:4]) if d[:4].isdigit() else "",
        "kind": kind,
        "poster": (IMG + poster) if poster else "",
        "tmdb": r.get("id"),
        "lang": r.get("original_language") or "",
        "r": round((r.get("vote_average") or 0), 1),
        "v": r.get("vote_count") or 0,
        "ov": (r.get("overview") or "")[:260],
        "platform": "",
    }


def month_bounds(start, n):
    out = []
    y, m = start.year, start.month
    for _ in range(n):
        first = datetime.date(y, m, 1)
        last = (datetime.date(y + (m // 12), (m % 12) + 1, 1)) - datetime.timedelta(days=1)
        out.append((f"{y}-{m:02d}", first.isoformat(), last.isoformat()))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/calendar.json.gz")
    ap.add_argument("--months", type=int, default=4)
    a = ap.parse_args()

    key = os.environ.get("TMDB_API_KEY", "").strip()
    if not key:
        print("TMDB_API_KEY is not set"); sys.exit(1)

    today = datetime.date.today()
    months = month_bounds(today, a.months)
    out = {"updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "countries": {c: n for c, n in COUNTRIES}, "months": {}}

    for label, first, last in months:
        out["months"][label] = {}
        print(f"\n{label}  ({first} → {last})")

        for code, cname in COUNTRIES:
            entry = {"theatre": [], "digital": []}

            for kind, rtype in KINDS:
                rows, seen = [], set()
                for page in (1, 2):
                    d = get("/discover/movie", key,
                            region=code, with_release_type=rtype,
                            sort_by="popularity.desc", page=page,
                            **{"primary_release_date.gte": first,
                               "primary_release_date.lte": last,
                               "vote_count.gte": 2})
                    for r in (d or {}).get("results", []):
                        if r.get("id") in seen:
                            continue
                        seen.add(r.get("id"))
                        s = shape(r, kind)
                        if s["date"]:
                            rows.append(s)
                entry[kind] = rows

            # which platform, for India's digital releases — that is the point of the calendar
            if code == "IN" and entry["digital"]:
                for s in entry["digital"][:60]:
                    p = get(f"/movie/{s['tmdb']}/watch/providers", key)
                    res = ((p or {}).get("results") or {}).get("IN") or {}
                    names = []
                    for bucket in ("flatrate", "free", "ads"):
                        for prov in (res.get(bucket) or []):
                            n = prov.get("provider_name")
                            if n and n not in names:
                                names.append(n)
                    s["platform"] = " · ".join(names[:3])
                    time.sleep(0.12)

            out["months"][label][code] = entry
            print(f"  {cname:16s} theatre {len(entry['theatre']):>3}  digital {len(entry['digital']):>3}")

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with gzip.open(a.out, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    total = sum(len(v["theatre"]) + len(v["digital"])
                for m in out["months"].values() for v in m.values())
    print(f"\nwrote {a.out}  {os.path.getsize(a.out)/1024:.1f} KB  ·  {total} entries")


if __name__ == "__main__":
    main()
