# ============================================================================
#  FilmiSet — enrich the titles the site actually carries, in about seven minutes
#
#  Paste into a Colab cell and run. No Drive, no database, no GitHub token: it
#  reads the same JSON the live site reads, straight from the deployed site, so
#  what comes out lines up exactly with what is on screen.
#
#  Why start here instead of at 12.8 million: 10,000 titles is about 20,000 TMDB
#  calls, which is seven minutes. The whole catalogue is 160 hours across fifteen
#  sittings. Making the ten thousand perfect first means you can see the result
#  today, and the same script scales up afterwards by pointing it at a bigger list.
#
#  Output, written to Drive so it survives the session:
#    Drive/Filmiset_Data/enrich_10k/enrich_aa.json.gz ... + manifest
#  Each record: {p: poster path, o: overview, r: rating, w: [provider ids],
#                s: seasons, e: episodes}
# ============================================================================

from google.colab import drive
drive.mount('/content/drive')

import os, json, gzip, re, time, unicodedata, urllib.request, urllib.parse, urllib.error

SITE = 'https://filmiset.vercel.app'
OUT = '/content/drive/MyDrive/Filmiset_Data/enrich_10k'
os.makedirs(OUT, exist_ok=True)

# ---- the key ---------------------------------------------------------------
TMDB_KEY = os.environ.get('TMDB_API_KEY', '')
if not TMDB_KEY:
    try:
        from google.colab import userdata
        TMDB_KEY = userdata.get('TMDB_API_KEY')
    except Exception:
        pass
if not TMDB_KEY:
    TMDB_KEY = input('Paste your TMDB API key: ').strip()

TMDB = 'https://api.themoviedb.org/3'

def tmdb(path, **params):
    params['api_key'] = TMDB_KEY
    url = f'{TMDB}{path}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

try:
    tmdb('/configuration')
    print('TMDB key verified ✓')
except Exception as e:
    raise SystemExit(f'TMDB key rejected: {type(e).__name__} {e}')

# ---- gather the titles the site shows --------------------------------------
# The site merges ~30 files. Read them all from the deployed site so nothing is
# guessed and nothing depends on having the repo locally.
FILES = """catalog.json curated_hindi.json curated_hollywood.json curated_series.json
curated_hollywood_series.json curated_anime.json curated_netflix.json curated_netflix_series.json
curated_netflix_hollywood.json curated_prime.json curated_hotstar.json curated_gujarati.json
curated_multiott.json curated_sonyliv_zee5.json curated_india1.json curated_india2.json
curated_india_all.json curated_canons.json curated_shortfilms.json curated_youtube_free.json
curated_youtube_free2.json curated_indian_starter.json curated_situations.json imdb_indian.json
tmdb.json jikan.json movies.json""".split()

rows = {}
for name in FILES:
    try:
        req = urllib.request.Request(f'{SITE}/data/{name}', headers={'User-Agent':'FilmiSet/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8','ignore'))
    except Exception as e:
        print(f'  skip {name}: {type(e).__name__}')
        continue
    items = data if isinstance(data, list) else (data.get('titles') if isinstance(data, dict) else [])
    if not isinstance(items, list):
        continue
    for it in items:
        if not isinstance(it, dict): continue
        t = it.get('t') or it.get('title') or it.get('name')
        if not t: continue
        k = re.sub(r'[^a-z0-9]+',' ', str(t).lower()).strip()
        if k and k not in rows:
            rows[k] = {'t': str(t), 'y': it.get('y') or it.get('year'),
                       'type': it.get('type') or 'Movie',
                       'imdb': it.get('id') or it.get('tconst') or ''}
    print(f'  {name}: {len(items)} rows (total unique {len(rows):,})')

print(f'\ntitles to enrich: {len(rows):,}')

# ---- the work --------------------------------------------------------------
def bucket(t):
    n = re.sub(r'[^a-z0-9]+',' ', str(t).lower()).strip()
    n = re.sub(r'\b(the|a|an)\b',' ', n).strip()
    if len(n) >= 2 and n[0].isalpha() and n[1].isalpha(): return n[:2]
    if n and n[0].isalpha(): return n[0] + '_'
    return '_other'

def load_bucket(b):
    p = f'{OUT}/enrich_{b}.json.gz'
    if os.path.exists(p):
        try: return json.loads(gzip.open(p,'rt',encoding='utf-8').read())
        except Exception: return {}
    return {}

buckets = {}
done = 0
found = 0
started = time.time()

for k, row in rows.items():
    kind = 'tv' if str(row['type']).lower() in ('series','tvseries','tvminiseries','show') else 'movie'
    rec = {}
    try:
        params = {'query': row['t'][:200], 'include_adult': 'false'}
        if row['y']: params['first_air_date_year' if kind=='tv' else 'year'] = row['y']
        hits = tmdb(f'/search/{kind}', **params).get('results') or []
        if not hits and row['y']:
            # a wrong year is common in catalogue data; retry without it
            params.pop('first_air_date_year', None); params.pop('year', None)
            hits = tmdb(f'/search/{kind}', **params).get('results') or []
        done += 1
        if hits:
            tid = hits[0]['id']
            det = tmdb(f'/{kind}/{tid}')
            if det.get('poster_path'):  rec['p'] = det['poster_path']
            if (det.get('overview') or '').strip(): rec['o'] = det['overview'].strip()[:220]
            if det.get('vote_average'): rec['r'] = round(float(det['vote_average']),1)
            if det.get('number_of_seasons'):  rec['s'] = det['number_of_seasons']
            if det.get('number_of_episodes'): rec['e'] = det['number_of_episodes']
            try:
                wp = tmdb(f'/{kind}/{tid}/watch/providers').get('results') or {}
                ids = set()
                for region in ('IN','US','GB'):
                    block = wp.get(region) or {}
                    for b in ('flatrate','free','ads'):
                        for pr in block.get(b) or []:
                            if pr.get('provider_id'): ids.add(pr['provider_id'])
                if ids: rec['w'] = sorted(ids)
            except Exception:
                pass
            if rec:
                b = bucket(row['t'])
                buckets.setdefault(b, {})[row['imdb'] or k] = rec
                found += 1
    except Exception:
        time.sleep(0.4)
        continue
    if done % 250 == 0:
        rate = done / max(1, time.time()-started)
        left = len(rows) - done
        print(f'  {done:,}/{len(rows):,} | {found:,} enriched | {rate:.0f}/s | ~{left/max(1,rate)/60:.0f} min left', flush=True)
    time.sleep(0.04)          # ~25/s, comfortably inside TMDB's limit

# ---- write -----------------------------------------------------------------
manifest = {'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'titles': len(rows), 'enriched': found, 'buckets': {}}
for b, data in buckets.items():
    p = f'{OUT}/enrich_{b}.json.gz'
    with gzip.open(p, 'wt', encoding='utf-8', compresslevel=6) as f:
        json.dump(data, f, ensure_ascii=False, separators=(',',':'))
    manifest['buckets'][b] = {'n': len(data), 'bytes': os.path.getsize(p)}

json.dump(manifest, open(f'{OUT}/manifest.json','w'), separators=(',',':'))
total = sum(v['bytes'] for v in manifest['buckets'].values())
print(f'\nDONE in {(time.time()-started)/60:.1f} min')
print(f'  titles checked : {done:,}')
print(f'  enriched       : {found:,} ({found/max(1,len(rows))*100:.0f}%)')
print(f'  files          : {len(buckets)}')
print(f'  total size     : {total/1024**2:.2f} MB')
print(f'  output folder  : {OUT}')
print('\nShare the Drive folder or tell me it is done — the site can then read these directly.')
