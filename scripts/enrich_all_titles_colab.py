# ============================================================================
#  FilmiSet — enrich every title: poster path, overview, OTT providers
#
#  Paste into a Colab cell and run. Re-run it as many times as you like: it
#  remembers what it has already done and picks up where it stopped. That is the
#  whole point — 12.8M TMDB lookups at the rate TMDB allows is about 71 hours of
#  pure calls, so this cannot finish in one sitting.
#
#  THE TRICK THAT MAKES THIS POSSIBLE
#  We do not store images. 12.8M posters at 25 KB each is 322 GB and that is not
#  a thing anyone can host for free. We store the *path* instead — about 20 bytes
#  — and let the browser fetch the picture from TMDB's own CDN, which costs us
#  nothing and is already fast. Same for the overview (capped) and the providers.
#
#  Output, all resumable:
#    Drive/Filmiset_Data/enrich/progress.json          what is done so far
#    Drive/Filmiset_Data/enrich/enrich_aa.json.gz ...   poster path, overview, providers
#    Drive/Filmiset_Data/enrich/enrich_manifest.json
# ============================================================================

from google.colab import drive
drive.mount('/content/drive')

import os, glob, json, gzip, re, time, unicodedata, sqlite3, urllib.request, urllib.parse

# ---- where things are -------------------------------------------------------
DB_CANDIDATES = ['/content/drive/MyDrive/filmiset_all_world_master_15m.db',
                 '/content/drive/MyDrive/Filmiset_Data/filmiset_all_world_master_15m.db']
DB = next((p for p in DB_CANDIDATES if os.path.exists(p)), None)
if not DB:
    hits = glob.glob('/content/drive/MyDrive/**/filmiset_all_world_master_15m.db', recursive=True)
    DB = hits[0] if hits else None
assert DB, 'master DB not found in Drive'

OUT = '/content/drive/MyDrive/Filmiset_Data/enrich'
os.makedirs(OUT, exist_ok=True)
PROGRESS = f'{OUT}/progress.json'

# ---- the key ---------------------------------------------------------------
# In Colab, store it once as a secret or just paste it here for the session.
# Never commit this file with a key in it.
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
IMG = 'https://image.tmdb.org/t/p/w200'

def tmdb(path, **params):
    params['api_key'] = TMDB_KEY
    url = f'{TMDB}{path}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

# prove the key before doing anything expensive — a rejected key looks exactly
# like a missing one, and that is how three files stayed empty for days
try:
    tmdb('/configuration')
    print('TMDB key verified ✓')
except Exception as e:
    raise SystemExit(f'TMDB key rejected: {type(e).__name__} {e}')

# ---- the database ----------------------------------------------------------
con = sqlite3.connect(DB)
cur = con.cursor()
cols = [r[1] for r in cur.execute('PRAGMA table_info(all_world_media)')]
def pick(*names):
    for n in names:
        for c in cols:
            if c.lower() == n.lower(): return c
C_TITLE = pick('title','primaryTitle','t')
C_YEAR  = pick('year','startYear','y')
C_TYPE  = pick('type','titleType','kind')
C_ID    = pick('imdb_id','tconst','id')
print('using:', C_TITLE, C_YEAR, C_TYPE, C_ID)
assert C_TITLE and C_ID

where = f"WHERE ({C_TYPE} IS NULL OR lower({C_TYPE}) NOT IN ('episode','tvEpisode'))" if C_TYPE else ""
rows = cur.execute(f"SELECT {C_ID},{C_TITLE},{C_YEAR},{C_TYPE} FROM all_world_media {where}").fetchall()
print(f'titles to enrich: {len(rows):,}')

# ---- resume ----------------------------------------------------------------
done = set()
if os.path.exists(PROGRESS):
    done = set(json.load(open(PROGRESS)))
    print(f'resuming — {len(done):,} already done')

# ---- normalise + bucket, same as the site ----------------------------------
def norm(t):
    t = unicodedata.normalize('NFKD', str(t or '')).encode('ascii','ignore').decode()
    t = t.lower().replace('&','and')
    t = re.sub(r'[^a-z0-9]+',' ', t)
    return re.sub(r'\s+',' ', re.sub(r'\b(the|a|an)\b',' ', t)).strip()

def bucket(t):
    n = norm(t)
    if len(n) >= 2 and n[0].isalpha() and n[1].isalpha(): return n[:2]
    if n and n[0].isalpha(): return n[0] + '_'
    return '_other'

def load_bucket(b):
    p = f'{OUT}/enrich_{b}.json.gz'
    if os.path.exists(p):
        try: return json.loads(gzip.open(p,'rt',encoding='utf-8').read())
        except Exception: return {}
    return {}

def save_bucket(b, data):
    with gzip.open(f'{OUT}/enrich_{b}.json.gz','wt',encoding='utf-8',compresslevel=6) as f:
        json.dump(data, f, ensure_ascii=False, separators=(',',':'))

# ---- the work --------------------------------------------------------------
# How long to run this sitting. Colab kills a session around 12h; leave headroom.
MAX_MINUTES = 660
started = time.time()
lookups = 0
found = 0
dirty = set()

for imdb, title, year, typ in rows:
    if imdb in done:
        continue
    if (time.time() - started) / 60 > MAX_MINUTES:
        print('time budget reached — saving and stopping')
        break
    kind = 'tv' if str(typ or '').lower() in ('tvseries','tvminiseries','tvepisode','series') else 'movie'
    try:
        params = {'query': str(title)[:200], 'include_adult': 'false'}
        if year: params['first_air_date_year' if kind=='tv' else 'year'] = year
        hits = tmdb(f'/search/{kind}', **params).get('results') or []
        lookups += 1
        if not hits:
            done.add(imdb)
        else:
            tid = hits[0]['id']
            # one detail call gives overview + poster; providers is a second call
            det = tmdb(f'/{kind}/{tid}')
            rec = {}
            if det.get('poster_path'):  rec['p'] = det['poster_path']          # ~20 bytes
            ov = (det.get('overview') or '').strip()
            if ov:                      rec['o'] = ov[:220]                     # capped
            if det.get('vote_average'): rec['r'] = round(float(det['vote_average']),1)
            if det.get('number_of_seasons'): rec['s'] = det['number_of_seasons']
            if det.get('number_of_episodes'): rec['e'] = det['number_of_episodes']
            try:
                wp = tmdb(f'/{kind}/{tid}/watch/providers').get('results') or {}
                ids = set()
                for region in ('IN','US','GB'):
                    block = wp.get(region) or {}
                    for k in ('flatrate','free','ads'):
                        for pr in block.get(k) or []:
                            ids.add(pr.get('provider_id'))
                if ids: rec['w'] = sorted(x for x in ids if x)
            except Exception:
                pass
            if rec:
                b = bucket(title)
                data = load_bucket(b)
                data[imdb] = rec
                save_bucket(b, data)
                found += 1
                dirty.add(b)
            done.add(imdb)
    except Exception as e:
        # a network blip should not lose the whole run
        time.sleep(0.5)
        continue
    if lookups % 200 == 0:
        json.dump(sorted(done), open(PROGRESS,'w'))
        rate = lookups / max(1,(time.time()-started))
        left = len(rows) - len(done)
        print(f'  {lookups:,} lookups | {found:,} enriched | {rate:.0f}/s | {left:,} left '
              f'| ~{left/max(1,rate)/3600:.1f}h remaining', flush=True)
    time.sleep(0.045)          # ~22/s, comfortably inside TMDB's limit

json.dump(sorted(done), open(PROGRESS,'w'))
print(f'\nthis sitting: {lookups:,} lookups, {found:,} enriched')
print(f'total done  : {len(done):,} of {len(rows):,}')
print('run the cell again to continue')
