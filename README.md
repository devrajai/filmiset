# FilmiSet

Mood, language aur **"where to watch"** ke hisaab se movie discovery site.

Ek single-file static site — koi build step nahi, koi API key nahi. Catalog ek **Google Sheet** se aata hai.

## Categories
- Bollywood (Hindi cinema)
- Hollywood (English cinema)
- Gujarati Movies
- Gujarati Natak
- South (Hindi Dubbed)
- Korean (Hindi Dubbed)
- Anime (Japanese animation)
- Animation (all animated films)

Titles are both **movies** and **web / TV series** (Type filter).

## Features
- Mood filters (Feel-Good, Comedy, Romantic, Thriller, Mystery, Action, Emotional, Horror, Nostalgic, Family)
- Type filter (Movie / Natak / Series) + live search
- Era filter (Classic pre-2000 / Modern) + a "Classic" badge on old titles
- Festival / Occasion filter (Diwali, Holi, Weekend, Family Night, Independence Day, New Year, Rainy Day)
- Release filter — **New (this year)** and **Upcoming** (with release dates, sorted by date)
- **Hindi Dubbed** filter — shows every title with a Hindi dub, regardless of original language
- **OTT Platform** filter (Netflix, Prime Video, JioHotstar, ZEE5, SonyLIV, HBO Max, Apple TV+, Crunchyroll, …)
- **Collections** — Heist, Suspense & Mystery, Thriller, Crime, Horror, Teen, Romance, Sci-Fi, Action, Comedy, 18+ (Adult), Most Popular
- **Franchise** — Marvel (MCU), DC, James Bond, Fast & Furious, Harry Potter, Star Wars, Mission: Impossible, Jurassic Park, Transformers, Pirates, Hunger Games, Twilight, Fifty Shades, Lord of the Rings — always shown in **release order (story sequence)**
- **Sort** — Newest / Most popular (popularity from Wikidata sitelinks)
- Har title par: year, genres, mood tags, available audio (Hindi dub included), OTT platforms
- **"Where to watch"** button -> JustWatch India search (100% legal)


> The **Catalog** sheet also has an **Occasion Tags** column (Diwali, Holi, Weekend, …). The
> site uses those tags when present, and falls back to a mood/genre mapping when a row is blank —
> so you can edit the festival picks yourself without touching any code.

## Structure
```
index.html                        # the whole site (HTML + CSS + JS)
data/movies.json                  # curated catalog (from the Google Sheet)
data/catalog.json                 # auto-collected catalog (Wikidata) — refreshed daily
posters/                          # compressed poster images (~19 KB each, stored locally)
scripts/sheet_to_json.py          # Google Sheet (Catalog tab) -> data/movies.json
scripts/fetch_data.py             # Wikidata (free, no key) -> data/catalog.json
scripts/download_posters.py       # download + compress posters -> posters/
scripts/fetch_youtube.py          # YouTube channel RSS (free, no key) -> data/youtube.json
scripts/fetch_ott.py              # TMDB watch-providers -> fills each title's OTT list
channels.txt                      # the YouTube channels to collect from
data/youtube.json                 # trailers / promos collected from those channels
.github/workflows/update-data.yml # daily job that refreshes data/catalog.json
```

The site fetches `data/movies.json` on load and merges it with a small embedded
demo set (which acts as an offline fallback). If the fetch fails — e.g. you opened
the file directly with `file://` — it still renders the demo data.

## Update the catalog
1. Edit the **Catalog** tab in the Google Sheet (add/change rows).
2. Regenerate the JSON — either:
   - **Published CSV (no credentials):** in Sheets, `File -> Share -> Publish to web`,
     pick the *Catalog* sheet, choose **CSV**, copy the link, then
     ```
     python3 scripts/sheet_to_json.py --url "https://docs.google.com/.../pub?gid=0&single=true&output=csv"
     ```
   - **Downloaded CSV:** `File -> Download -> CSV`, then
     ```
     python3 scripts/sheet_to_json.py --csv ~/Downloads/FilmiSet.csv
     ```
3. Commit the updated `data/movies.json`. The site picks it up automatically.

## Auto-refreshed catalog (free, no API key)
`scripts/fetch_data.py` pulls real film data from **Wikidata** (free, no key, no sign-up) and
writes `data/catalog.json`. A GitHub Action (`.github/workflows/update-data.yml`) runs it every
day at 08:00 IST and commits the result — so the site keeps itself current with zero effort.

Run it by hand:
```
python3 scripts/fetch_data.py --out data/catalog.json      # all languages
python3 scripts/fetch_data.py --langs Hindi,Gujarati       # just some
```

Sources used: Wikidata Query Service (titles, years, genres, descriptions) and Wikimedia
Commons (poster images, loaded by the browser). OTT availability and Hindi-dub flags are not
available from a free no-key source, so those stay curated in the Google Sheet.


## Posters (stored locally, compressed)
Posters are downloaded once and stored in `posters/` — resized to 300px wide and
re-encoded as JPEG (~19 KB each), so the site does not hotlink Wikipedia/Wikimedia
(which is discouraged and rate-limited). Refresh them with:
```
python3 scripts/download_posters.py            # resumes; skips images already on disk
```

> **Pipeline order:** `fetch_data.py` (Wikidata, incl. upcoming films) -> `download_posters.py`
> (compress + localise posters). Run both, then commit.


## YouTube channels (free, no key)
`scripts/fetch_youtube.py` reads `channels.txt` and pulls each channel's latest videos from its
public **RSS feed** (`youtube.com/feeds/videos.xml`) — no API key, no quota. A handle (`@Name`)
is resolved to a channel id automatically. Each video becomes a card with its thumbnail and a
**Watch on YouTube** button, tagged with a red **YouTube** badge and filterable via *Source →
YouTube*.

Add channels to `channels.txt`:
```
# handle-or-channel-id | category | original-language | display name
ShemarooGujarati | gujarati-movie | Gujarati | Shemaroo Gujarati
GoldminesTelefilms | south-dubbed | Hindi | Goldmines
```
Then run:
```
python3 scripts/fetch_youtube.py
python3 scripts/download_posters.py     # localise + compress the thumbnails
```



## Backups (no downloads needed)
The whole catalogue is backed up automatically:
* **Google Sheet** — tabs *Full Catalog* (all titles + OTT + popularity) and *OTT Summary*.
* **Google Drive** — `FilmiSet-backup.xlsx` (same workbook, refreshed by the workflow).
* **Repo** — `data/*.json` plus `data/filmiset-backup.xlsx`, committed daily.

## OTT availability (TMDB — optional, free key)
Every card already links to **JustWatch** for "where to watch". To also fill the
**OTT Platform** filter for *all* titles, add a free TMDB key:

1. Create a free account at themoviedb.org -> **Settings -> API** -> copy the **API Key (v3)**.
2. In this GitHub repo: **Settings -> Secrets and variables -> Actions -> New repository secret**,
   name it `TMDB_API_KEY`, paste the key.
3. The daily workflow will now fill OTT info automatically (or run it by hand):
   ```
   TMDB_API_KEY=xxxx python3 scripts/fetch_ott.py --region IN
   ```

Without the key the step is skipped and the site keeps working — OTT info then comes
only from the curated Google Sheet (OTT Platforms column) and YouTube.

## Run locally
```
python3 -m http.server 8000   # then open http://localhost:8000
```
(opening `index.html` directly also works, but the JSON fetch needs a server.)

## Data sources (roadmap)
- **Titles / genres / language / posters** -> TMDB API (free key)
- **"Kahan dekho"** -> JustWatch / Streaming Availability API
- **Hindi-dubbed + Gujarati-natak + old classics** -> curated in the Google Sheet

## Roadmap
- [ ] TMDB API integration (serverless function se key chhupana)
- [ ] More old / regional classics in the sheet
- [ ] Festival / weekend curated sections
- [ ] Watchlist (localStorage)

## Legal
Saare watch-links legal OTT platforms (JioHotstar, Prime Video, Netflix, ShemarooMe,
JOJO, MX Player) aur JustWatch search par le jaate hain.
**Koi piracy ya free-download link nahi.** Site kisi content ko host nahi karti —
sirf availability dikhati hai.
