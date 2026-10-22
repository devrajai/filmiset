# FilmiSet — how big can this get, and how

*Verified limits and the ladder from 2,400 to 15,000,000 titles.*

## What we measured (not guessed)

| Storage / host | Hard limit | Can the browser read it live? |
|---|---|---|
| **GitHub Pages** (the site itself) | **1 GB** published site, **100 MB** per file, ~100 GB/month bandwidth | yes (it *is* the site) |
| **GitHub repo** (raw / jsDelivr CDN) | ~1 GB soft, 5 GB hard; jsDelivr caps 50 MB per file | yes, via jsDelivr (CORS ok) |
| **Google Drive** | 15 GB free | **NO** — tested: 403 and **no `access-control-allow-origin`**, so `fetch()` from the site is blocked. Backups only. |
| **Google Sheets** (gviz endpoint) | **10,000,000 cells** per spreadsheet | **YES** — tested: returns `access-control-allow-origin`, and supports **server-side SQL**: `tq=select A,B,E,G,J where A contains 'Khan' limit 5` |
| **Free hosted DB** (Turso 9 GB, Cloudflare D1 5 GB) | ~9 GB | yes, via its HTTP API |

### The two numbers that decide everything

* **Metadata**: ~500 bytes per title in JSON → **10 M titles ≈ 5 GB**, 15 M ≈ 7.5 GB.
  GitHub Pages allows 1 GB total, and a browser cannot hold 5 GB of JSON in memory anyway.
* **Posters**: ~20 KB each → **10 M posters ≈ 200 GB**. There is no free host that stores that.

**Conclusion:** 10–15 M titles can never live inside the Pages site or in the repo. They need
(a) a queryable store that the page talks to, and (b) posters that are *linked*, not stored.

## The ladder

| Step | Titles | How | New signup? |
|---|---|---|---|
| now | ~2,400 | Wikidata + TMDB + curated JSON in the repo | no |
| **1** | **~100 k** | IMDb dumps ingested by the Action, shipped as sharded JSON in the repo | no |
| **2** | **~1 M** | the same rows written into the **Google Sheet** and queried live through the gviz endpoint (10 M cell cap) | no |
| **3** | **~15 M** | the IMDb rows in a **free hosted database** (Turso / Cloudflare D1) queried through its HTTP API | yes — one free account |

Posters at every step: **do not store them**. Link to TMDB's image CDN (`image.tmdb.org`) and
Wikipedia's upload URLs. Both are public, need no key, and keep working **after the TMDB API
key is disconnected**.

## Where the 15 M rows come from (free, no key)

IMDb publishes its whole catalogue as TSV dumps at `datasets.imdbws.com`:

* `title.basics.tsv.gz` — **~11.6 million rows** (movies, shorts, series, episodes, games…)
* `title.ratings.tsv.gz` — rating + vote count
* `title.akas.tsv.gz` — alternate / regional titles (Hindi, Gujarati, Tamil …)

`scripts/fetch_imdb_catalog.py` already downloads both, keeps the real titles
(drops the ~8 M individual `tvEpisode` rows and adult titles), joins the ratings, and writes
`data/imdb_stats.json` (true counts) plus `data/imdb_top.json` (the most-voted slice the site
can actually display today).

## What step 3 needs

1. One free database account — **Turso** (turso.tech, sign in with GitHub, 9 GB free) or
   **Cloudflare D1** (5 GB free).
2. Two repo secrets: `TURSO_URL`, `TURSO_TOKEN`.
3. A new Action step that loads `data/imdb_full.tsv.gz` into the database once a day.
4. The site switches from "download every row" to "ask the API for one page at a time"
   (search, filters, sort and pagination all happen server-side).

Until step 3, **step 2 (the Google Sheet, ~1 M titles) is the best free ceiling** — it needs no
new account and the browser can already query it.

## Why not just put it all in the Sheet?

A spreadsheet caps at 10 M cells. Ten columns per title means **1,000,000 titles** — after that
Sheets refuses to grow, and a single gviz response also gets slow. 15 M titles need 150 M cells.
