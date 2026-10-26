# ============================================================================
#  FilmiSet — build the search index from the master DB
#
#  Paste this whole file into one Colab cell and run it. It reads the master
#  SQLite database from Drive and writes a prefix-split index into Drive, ready
#  for the site to fetch one small file at a time.
#
#  Why prefix-split: 12.8 million titles is about 0.54 GB of JSON, or 0.14 GB
#  gzipped — far too much for one file and far too much for a phone. Split by
#  the first two letters of the normalised title, each file is roughly 200 KB
#  gzipped and loads in about a tenth of a second. Someone typing "go" fetches
#  index_go.json.gz and searches the 12.8M catalogue through that slice alone.
#
#  Output: Drive/Filmiset_Data/index/index_aa.json.gz ... index_zz.json.gz
#          Drive/Filmiset_Data/index/index_manifest.json
# ============================================================================

# ---- 1. mount Drive and find the database -----------------------------------
from google.colab import drive
drive.mount('/content/drive')

import os, glob
DB_CANDIDATES = [
    '/content/drive/MyDrive/filmiset_all_world_master_15m.db',
    '/content/drive/MyDrive/Filmiset_Data/filmiset_all_world_master_15m.db',
]
DB = next((p for p in DB_CANDIDATES if os.path.exists(p)), None)
if not DB:
    hits = glob.glob('/content/drive/MyDrive/**/filmiset_all_world_master_15m.db', recursive=True)
    DB = hits[0] if hits else None
print('database:', DB)
assert DB, 'master DB not found in Drive — check the filename'

OUT = '/content/drive/MyDrive/Filmiset_Data/index'
os.makedirs(OUT, exist_ok=True)

# ---- 2. look at the table before trusting it --------------------------------
import sqlite3
con = sqlite3.connect(DB)
cur = con.cursor()
cols = [r[1] for r in cur.execute('PRAGMA table_info(all_world_media)')]
print('columns:', cols)
print('rows   :', cur.execute('SELECT COUNT(*) FROM all_world_media').fetchone()[0])

# work out which column is which, without assuming
def pick(*names):
    for n in names:
        for c in cols:
            if c.lower() == n.lower():
                return c
    return None

C_TITLE = pick('title', 'primaryTitle', 't')
C_YEAR  = pick('year', 'startYear', 'y')
C_TYPE  = pick('type', 'titleType', 'kind')
C_ID    = pick('imdb_id', 'tconst', 'id')
C_PARENT= pick('parent_id', 'parentTconst', 'series_id')
print('using:', dict(title=C_TITLE, year=C_YEAR, type=C_TYPE, id=C_ID, parent=C_PARENT))
assert C_TITLE and C_ID, 'could not identify the title and id columns'

# ---- 3. normalise exactly the way the site does ----------------------------
import re, unicodedata
def norm(t):
    """Same normalisation the site uses, so the prefix a user types matches the file."""
    t = unicodedata.normalize('NFKD', str(t or '')).encode('ascii', 'ignore').decode()
    t = t.lower().replace('&', 'and')
    t = re.sub(r'[^a-z0-9]+', ' ', t)
    t = re.sub(r'\b(the|a|an)\b', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def bucket(t):
    """Two-letter bucket. Anything that does not start with two letters goes to _other."""
    n = norm(t)
    if len(n) >= 2 and n[0].isalpha() and n[1].isalpha():
        return n[:2]
    if len(n) >= 1 and n[0].isalpha():
        return n[0] + '_'
    return '_other'

# ---- 4. build the index ----------------------------------------------------
# episodes are dropped: they belong under their series, not in a title search
where = f"WHERE ({C_TYPE} IS NULL OR lower({C_TYPE}) NOT IN ('episode','tvEpisode'))" if C_TYPE else ""
q = f"SELECT {C_ID}, {C_TITLE}, {C_YEAR}, {C_TYPE} FROM all_world_media {where}"
print('query:', q)

buckets = {}
total = 0
for row in cur.execute(q):
    imdb, title, year, typ = row
    if not title:
        continue
    b = bucket(title)
    # compact record: id, title, year, type — the site expands it on arrival
    buckets.setdefault(b, []).append([imdb, str(title)[:120], year or 0,
                                      (typ or 'Movie')[:12]])
    total += 1
    if total % 500000 == 0:
        print(f'  {total:,} rows, {len(buckets)} buckets')

print(f'total titles indexed: {total:,} across {len(buckets)} buckets')

# ---- 5. write one gzipped file per bucket ----------------------------------
import gzip, json
manifest = {'generated': __import__('datetime').datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            'total': total, 'buckets': {}}
written = 0
for b, rows in sorted(buckets.items()):
    rows.sort(key=lambda r: (-(r[2] or 0), r[1].lower()))
    payload = json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode()
    path = f'{OUT}/index_{b}.json.gz'
    with gzip.open(path, 'wb', compresslevel=6) as f:
        f.write(payload)
    manifest['buckets'][b] = {'n': len(rows), 'bytes': os.path.getsize(path)}
    written += os.path.getsize(path)
    if written and len(manifest['buckets']) % 50 == 0:
        print(f'  wrote {len(manifest["buckets"])} files, {written/1024**2:.1f} MB so far')

json.dump(manifest, open(f'{OUT}/index_manifest.json', 'w'), separators=(',', ':'))
print(f'\nDONE — {len(manifest["buckets"])} files, {written/1024**2:.1f} MB total')
print(f'largest bucket: {max(manifest["buckets"].items(), key=lambda kv: kv[1]["bytes"])}')
print(f'output folder : {OUT}')
print('\nNext: zip the folder and send it, or share the Drive folder so the index can be')
print('committed to the site in one go.')
