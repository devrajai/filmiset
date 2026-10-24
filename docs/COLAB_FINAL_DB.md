# Building the final master DB in Colab

One notebook, run once, after the GitHub Action has finished collecting. It merges everything the
project knows into a single SQLite file in Drive, so the site no longer needs to ask anyone for
anything.

**What goes in**

| Table | Source | Rows (approx) |
|---|---|---|
| `titles` | IMDb bulk `title.basics` | 1.29 crore |
| `ratings` | IMDb bulk `title.ratings` | 17 lakh rated |
| `people` | IMDb bulk `name.basics` | 1.2 crore |
| `credits` | IMDb bulk `title.principals` | 9 crore |
| `akas` | IMDb bulk `title.akas` | — (original language, region) |
| `episodes` | IMDb bulk `title.episode` | 1 crore |
| `posters` | TMDB sweep + Wikidata P18 | ~10 lakh |
| `ott` | TMDB watch providers (IN) | snapshot |
| `boxoffice` | TMDB budget/revenue | partial |
| `curated` | our own hand-checked rows | 2,866 |
| `moods`, `situations` | our own tag files | 117 + 91 |

**Paste this into a Colab cell.** It is written to be re-runnable: it skips work already done and
saves after every stage, because Colab will disconnect you eventually.

```python
# ============================================================
# FilmiSet — build the final master DB (run once, after collection)
# ============================================================
import os, sqlite3, gzip, csv, io, urllib.request, json, time, sys

DRIVE = "/content/drive/MyDrive/Filmiset_Data"
DB    = f"{DRIVE}/filmiset_final.db"
CACHE = "/content/imdb"
os.makedirs(CACHE, exist_ok=True)
os.makedirs(DRIVE, exist_ok=True)

from google.colab import drive
drive.mount("/content/drive")

IMDB = {
    "basics":     "https://datasets.imdbws.com/title.basics.tsv.gz",
    "ratings":    "https://datasets.imdbws.com/title.ratings.tsv.gz",
    "names":      "https://datasets.imdbws.com/name.basics.tsv.gz",
    "principals": "https://datasets.imdbws.com/title.principals.tsv.gz",
    "akas":       "https://datasets.imdbws.com/title.akas.tsv.gz",
    "episode":    "https://datasets.imdbws.com/title.episode.tsv.gz",
}

def download(url, label):
    dest = os.path.join(CACHE, os.path.basename(url))
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  {label}: cached ({os.path.getsize(dest)/1e6:.0f} MB)"); return dest
    print(f"  {label}: downloading…", flush=True)
    urllib.request.urlretrieve(url, dest)
    print(f"  {label}: {os.path.getsize(dest)/1e6:.0f} MB"); return dest

def tsv(path, cols, where=None):
    """yield rows from an IMDb .tsv.gz, converting \\N to None"""
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as fh:
        header = next(fh).rstrip("\n").split("\t")
        idx = [header.index(c) for c in cols]
        for line in fh:
            p = line.rstrip("\n").split("\t")
            try: row = tuple(None if p[i] == "\\N" else p[i] for i in idx)
            except IndexError: continue
            if where and not where(row): continue
            yield row

con = sqlite3.connect(DB)
con.execute("PRAGMA journal_mode=WAL")
con.execute("PRAGMA synchronous=OFF")
cur = con.cursor()

SCHEMA = {
 "titles":   "CREATE TABLE IF NOT EXISTS titles (tconst TEXT PRIMARY KEY, type TEXT, title TEXT, orig TEXT, year INT, runtime INT, genres TEXT, adult INT)",
 "ratings":  "CREATE TABLE IF NOT EXISTS ratings (tconst TEXT PRIMARY KEY, rating REAL, votes INT)",
 "people":   "CREATE TABLE IF NOT EXISTS people (nconst TEXT PRIMARY KEY, name TEXT, birth INT, death INT, known TEXT)",
 "credits":  "CREATE TABLE IF NOT EXISTS credits (tconst TEXT, nconst TEXT, category TEXT, job TEXT, chars TEXT)",
 "akas":     "CREATE TABLE IF NOT EXISTS akas (tconst TEXT, title TEXT, region TEXT, lang TEXT, is_orig INT)",
 "episodes": "CREATE TABLE IF NOT EXISTS episodes (tconst TEXT PRIMARY KEY, parent TEXT, season INT, episode INT)",
}
for ddl in SCHEMA.values(): cur.execute(ddl)

def stage(name, sql, rows, chunk=100000):
    have = cur.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    if have:
        print(f"  {name}: already has {have:,} rows — skipping"); return
    buf, n = [], 0
    for r in rows:
        buf.append(r)
        if len(buf) >= chunk:
            cur.executemany(sql, buf); buf = []; n += chunk
            if n % 500000 == 0:
                print(f"    {name}: {n:,}", flush=True); con.commit()
    if buf: cur.executemany(sql, buf); n += len(buf)
    con.commit(); print(f"  {name}: {n:,} rows")

print("1/6 titles")
stage("titles", "INSERT OR REPLACE INTO titles VALUES (?,?,?,?,?,?,?,?)",
      tsv(download(IMDB["basics"], "title.basics"),
          ["tconst","titleType","primaryTitle","originalTitle","startYear","runtimeMinutes","genres","isAdult"]))

print("2/6 ratings")
stage("ratings", "INSERT OR REPLACE INTO ratings VALUES (?,?,?)",
      tsv(download(IMDB["ratings"], "title.ratings"), ["tconst","averageRating","numVotes"]))

print("3/6 people")
stage("people", "INSERT OR REPLACE INTO people VALUES (?,?,?,?,?)",
      tsv(download(IMDB["names"], "name.basics"),
          ["nconst","primaryName","birthYear","deathYear","knownForTitles"]))

print("4/6 credits (this is the big one — an hour or more)")
stage("credits", "INSERT INTO credits VALUES (?,?,?,?,?)",
      tsv(download(IMDB["principals"], "title.principals"),
          ["tconst","nconst","category","job","characters"]))

print("5/6 original language + region")
stage("akas", "INSERT INTO akas VALUES (?,?,?,?,?)",
      tsv(download(IMDB["akas"], "title.akas"),
          ["tconst","title","region","language","isOriginalTitle"],
          where=lambda r: r[4] == "1"))

print("6/6 episodes")
stage("episodes", "INSERT OR REPLACE INTO episodes VALUES (?,?,?,?)",
      tsv(download(IMDB["episode"], "title.episode"), ["tconst","parentTconst","seasonNumber","episodeNumber"]))

print("indexes (a few minutes)")
for sql in [
  "CREATE INDEX IF NOT EXISTS ix_titles_title ON titles(title)",
  "CREATE INDEX IF NOT EXISTS ix_titles_year  ON titles(year)",
  "CREATE INDEX IF NOT EXISTS ix_titles_type  ON titles(type)",
  "CREATE INDEX IF NOT EXISTS ix_cred_t  ON credits(tconst)",
  "CREATE INDEX IF NOT EXISTS ix_cred_n  ON credits(nconst)",
  "CREATE INDEX IF NOT EXISTS ix_akas_t  ON akas(tconst)",
  "CREATE INDEX IF NOT EXISTS ix_ep_parent ON episodes(parent)",
]:
    cur.execute(sql); con.commit()
cur.execute("ANALYZE"); con.commit()

print("\ncounts:")
for t in SCHEMA:
    print(f"  {t:10s} {cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>12,}")
print(f"\nDB: {DB}  ({os.path.getsize(DB)/1e9:.2f} GB)")
con.close()
```

## After it finishes

Run this second cell to merge in the files the GitHub Action produced (posters, OTT, box office,
and our own curated rows), so one file answers every question:

```python
import json, sqlite3, os
BASE = "https://raw.githubusercontent.com/devrajai/filmiset/main/data"
con = sqlite3.connect(DB); cur = con.cursor()

def pull(name):
    try:
        with urllib.request.urlopen(f"{BASE}/{name}", timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  {name}: {type(e).__name__}"); return None

for table, ddl in [
  ("posters",   "CREATE TABLE IF NOT EXISTS posters (tconst TEXT PRIMARY KEY, url TEXT)"),
  ("ott",       "CREATE TABLE IF NOT EXISTS ott (tconst TEXT, platform TEXT, region TEXT)"),
  ("boxoffice", "CREATE TABLE IF NOT EXISTS boxoffice (tconst TEXT PRIMARY KEY, budget INT, revenue INT, verdict TEXT)"),
  ("curated",   "CREATE TABLE IF NOT EXISTS curated (title TEXT, year INT, cat TEXT, type TEXT, genres TEXT, moods TEXT, audio TEXT, platforms TEXT, note TEXT)"),
]:
    cur.execute(ddl)

m = pull("imdb_posters.json") or {}
cur.executemany("INSERT OR REPLACE INTO posters VALUES (?,?)", list(m.items())); con.commit()
print(f"posters: {len(m):,}")

w = pull("watch_providers.json") or {}
rows = [(k, p, "IN") for k, v in w.items() for p in (v.get("p") or [])]
cur.executemany("INSERT INTO ott VALUES (?,?,?)", rows); con.commit()
print(f"ott: {len(rows):,}")

b = pull("boxoffice.json") or {}
cur.executemany("INSERT OR REPLACE INTO boxoffice VALUES (?,?,?,?)",
                [(k, v.get("budget"), v.get("revenue"), v.get("verdict")) for k, v in b.items()]); con.commit()
print(f"boxoffice: {len(b):,}")

for f in ["curated_hindi","curated_india_all","curated_youtube_free","curated_indian_starter","curated_situations"]:
    d = pull(f + ".json") or []
    if isinstance(d, list):
        cur.executemany("INSERT INTO curated VALUES (?,?,?,?,?,?,?,?,?)",
            [(r.get("t"), r.get("y"), r.get("cat"), r.get("type"),
              ",".join(r.get("g") or []), ",".join(r.get("m") or []),
              ",".join(r.get("a") or []), ",".join(r.get("o") or []), r.get("note")) for r in d if isinstance(r, dict)])
con.commit()
print("curated merged")

cur.execute("VACUUM"); con.commit(); con.close()
print(f"done — {DB}")
```

## The queries the site will need

```sql
-- a title page
SELECT t.*, r.rating, r.votes, p.url AS poster
FROM titles t LEFT JOIN ratings r USING(tconst) LEFT JOIN posters p USING(tconst)
WHERE t.tconst = ?;

-- an actor page: everything they were in, newest first
SELECT t.tconst, t.title, t.year, t.type, c.category, r.rating
FROM credits c JOIN titles t ON t.tconst = c.tconst
LEFT JOIN ratings r USING(tconst)
WHERE c.nconst = (SELECT nconst FROM people WHERE name = ?)
ORDER BY t.year DESC;

-- where to watch, and how it did
SELECT o.platform, b.verdict FROM ott o LEFT JOIN boxoffice b USING(tconst) WHERE o.tconst = ?;
```
