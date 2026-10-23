# Refreshing `filmiset_worldwide_catalog.db`

The database in the Drive folder (`Filmiset_Data`) is a **frozen snapshot** of IMDb. It will not
update itself. This is how to refresh it — and the honest reason it is a manual job rather than an
automatic one.

## Why not automatic

| Option | Verdict |
|---|---|
| Commit the .db to the repo | ✗ 370 MB, and GitHub rejects files over 100 MB |
| Build it in the GitHub Action | ✓ works, but the file lands as a **workflow artifact** (deleted after 90 days) — it cannot be pushed to your Drive without a service account |
| Build it in Colab, save to Drive | ✓ **this is what you already do, and it is the simplest** |

So: the *site's* data refreshes automatically every day; the *database backup* is refreshed on
demand, in Colab.

## The Colab cell

Open <https://colab.research.google.com>, make a new notebook, and paste this into one cell.
It takes roughly 10-15 minutes and writes the finished database straight to your Drive.

```python
# FilmiSet — rebuild the worldwide catalogue database and save it to Drive
import csv, gzip, os, sqlite3, urllib.request

from google.colab import drive
drive.mount('/content/drive')

FOLDER = '/content/drive/MyDrive/Filmiset_Data'      # the folder that holds everything
DB = f'{FOLDER}/filmiset_worldwide_catalog.db'
BASE = 'https://datasets.imdbws.com'
KEEP = {'movie', 'short', 'tvSeries', 'tvMiniSeries', 'tvMovie'}
os.makedirs(FOLDER, exist_ok=True)

def grab(name):
    if not os.path.exists(name):
        print('downloading', name, '…')
        urllib.request.urlretrieve(f'{BASE}/{name}', name)
    return name

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('DROP TABLE IF EXISTS global_media')
cur.execute('''CREATE TABLE global_media (
    imdb_id TEXT PRIMARY KEY, media_type TEXT, primary_title TEXT, original_title TEXT,
    release_year INTEGER, runtime_mins INTEGER, genres TEXT, rating REAL, vote_count INTEGER)''')
conn.commit()

# ratings first, so the big basics pass can join them on the fly
ratings = {}
with gzip.open(grab('title.ratings.tsv.gz'), 'rt', encoding='utf-8', newline='') as f:
    r = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE); next(r, None)
    for row in r:
        if len(row) >= 3:
            ratings[row[0]] = (float(row[1]), int(row[2]))

batch, total = [], 0
with gzip.open(grab('title.basics.tsv.gz'), 'rt', encoding='utf-8', newline='') as f:
    r = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE); next(r, None)
    for row in r:
        if len(row) < 9 or row[1] not in KEEP or row[4] == '1':
            continue
        tconst, ttype, title, otitle, _adult, year, _end, runtime, genres = row[:9]
        rt, votes = ratings.get(tconst, (None, None))
        batch.append((tconst, ttype, title, otitle,
                      int(year) if year.isdigit() else None,
                      int(runtime) if runtime.isdigit() else None, genres, rt, votes))
        if len(batch) >= 50000:
            cur.executemany('INSERT OR REPLACE INTO global_media VALUES (?,?,?,?,?,?,?,?,?)', batch)
            conn.commit(); total += len(batch); batch = []
            print(f'  {total:,} titles')
if batch:
    cur.executemany('INSERT OR REPLACE INTO global_media VALUES (?,?,?,?,?,?,?,?,?)', batch)
    conn.commit(); total += len(batch)

cur.execute('CREATE INDEX IF NOT EXISTS idx_type ON global_media(media_type)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_title ON global_media(primary_title)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_year ON global_media(release_year)')
conn.commit(); conn.close()

print(f'\ndone — {total:,} titles in {DB}')
print('now upload/replace it in the same Drive folder so the backup stays current')
```

## The same thing from the command line

`scripts/build_local_db.py` in the repo does the same job locally:

```
python3 scripts/build_local_db.py          # writes filmiset_global_titles.db (~370 MB)
```

It is deliberately **not** part of the daily workflow — the site does not read it, so rebuilding
it daily would cost time and storage for no benefit.

## When to refresh

Refresh the database when you want a new cold backup — for example right before switching the
APIs off, or every few months. Everything the **site** shows comes from the Sheets and the files
in `data/`, both of which update daily on their own.
