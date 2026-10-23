#!/usr/bin/env python3
"""build_local_db.py — optional: build a local SQLite index of every IMDb title.

This is a LOCAL analysis tool, not part of the site. FilmiSet serves its catalogue from Google
Sheets because a browser can query those directly (the gviz endpoint is CORS-enabled); a SQLite
file cannot be queried by a static site. So this database is for working offline: counting,
spot-checking, and building shard slices without repeatedly streaming the big IMDb dump.

    python3 scripts/build_local_db.py          # writes filmiset_global_titles.db (~500 MB)
"""
import csv
import gzip
import os
import sqlite3
import urllib.request

DB_FILE = "filmiset_global_titles.db"
DATASET_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"
LOCAL_ARCHIVE = "title.basics.tsv.gz"
TARGET_TYPES = {"movie", "short", "tvSeries", "tvMiniSeries", "tvMovie"}
BATCH = 50000


def main():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS global_catalog (
        imdb_id TEXT PRIMARY KEY, content_type TEXT, primary_title TEXT, original_title TEXT,
        release_year INTEGER, runtime_mins INTEGER, genres TEXT)""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_type ON global_catalog(content_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_title ON global_catalog(primary_title)")
    conn.commit()

    if not os.path.exists(LOCAL_ARCHIVE):
        print("downloading the IMDb archive (~180 MB compressed) …")
        urllib.request.urlretrieve(DATASET_URL, LOCAL_ARCHIVE)

    print("ingesting movies, series and shorts …")
    batch, total = [], 0
    with gzip.open(LOCAL_ARCHIVE, "rt", encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(r, None)
        for row in r:
            if len(row) < 9:
                continue
            tconst, ttype, title, otitle, adult, year, _end, runtime, genres = row[:9]
            if ttype not in TARGET_TYPES or adult == "1":
                continue
            batch.append((tconst, ttype, title, otitle,
                          int(year) if year.isdigit() else None,
                          int(runtime) if runtime.isdigit() else None, genres))
            if len(batch) >= BATCH:
                cur.executemany("INSERT OR IGNORE INTO global_catalog VALUES (?,?,?,?,?,?,?)", batch)
                conn.commit()
                total += len(batch)
                batch = []
                print(f"  {total:,} titles")
    if batch:
        cur.executemany("INSERT OR IGNORE INTO global_catalog VALUES (?,?,?,?,?,?,?)", batch)
        conn.commit()
        total += len(batch)
    conn.close()
    print(f"done — {total:,} titles in {DB_FILE}")


if __name__ == "__main__":
    main()
