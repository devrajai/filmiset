#!/usr/bin/env python3
"""fetch_tmdb_exports.py — TMDB's daily ID exports (no API key needed).

TMDB publishes a full ID dump every day at files.tmdb.org/p/exports/:

    movie_ids_MM_DD_YYYY.json.gz        ~1.2M movie ids
    tv_series_ids_MM_DD_YYYY.json.gz    ~250k series ids

Each line is {id, original_title/original_name, popularity, adult}. That is the whole TMDB
catalogue in two small files — far cheaper than paging /discover year by year — and popularity
is useful for ranking. No key, no rate limit.

Writes data/tmdb_exports.json with the titles that clear a popularity floor (the long tail of
zero-popularity entries is dropped, since it adds rows without adding anything a viewer wants).

    python3 scripts/fetch_tmdb_exports.py --min-popularity 1
"""
import argparse, datetime, gzip, json, os, sys, urllib.request

BASE = "https://files.tmdb.org/p/exports"
OUT = "data/tmdb_exports.json"


def fetch(kind, day, tmp):
    name = f"{kind}_ids_{day}.json.gz"
    url = f"{BASE}/{name}"
    if not os.path.exists(tmp):
        print(f"  downloading {name} …")
        req = urllib.request.Request(url, headers={"User-Agent": "FilmiSet/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            f.write(r.read())
    return tmp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-popularity", type=float, default=1.0)
    ap.add_argument("--days-back", type=int, default=3, help="try today, then go back a few days")
    args = ap.parse_args()

    rows = []
    for kind, label in (("movie", "Movie"), ("tv_series", "Series")):
        got = None
        for back in range(args.days_back + 1):
            day = (datetime.date.today() - datetime.timedelta(days=back)).strftime("%m_%d_%Y")
            tmp = f"/tmp/{kind}_ids_{day}.json.gz"
            try:
                got = fetch(kind, day, tmp)
                break
            except Exception as e:
                print(f"  {kind} {day}: {type(e).__name__}", file=sys.stderr)
        if not got:
            print(f"  could not fetch the {kind} export", file=sys.stderr)
            continue
        n = kept = 0
        try:
            with gzip.open(got, "rt", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        it = json.loads(line)
                    except Exception:
                        continue
                    n += 1
                    if it.get("adult"):
                        continue
                    pop = float(it.get("popularity") or 0)
                    if pop < args.min_popularity:
                        continue
                    title = it.get("original_title") or it.get("original_name") or ""
                    if not title:
                        continue
                    kept += 1
                    rows.append({"id": "tmdb-" + str(it.get("id")), "t": title, "y": "",
                                 "type": label, "pop": round(pop, 1)})
        except Exception as e:
            print(f"  could not read {got}: {type(e).__name__} {e}", file=sys.stderr)
            continue
        print(f"  {kind}: {n:,} ids, kept {kept:,} above popularity {args.min_popularity}")

    rows.sort(key=lambda r: -r["pop"])
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    mb = os.path.getsize(OUT) / 1048576
    print(f"wrote {OUT}: {len(rows):,} titles ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
