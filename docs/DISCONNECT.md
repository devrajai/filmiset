# Turning the APIs off — the final state of FilmiSet

The goal: once collection is finished, the site must run **with no API keys and no third-party
services at runtime**. Everything it shows has to be stored data.

This is already true of the running site — it reads Google Sheets and files in `data/`. The
external services are used only by the daily GitHub Action to *build* those files. So
"disconnecting" means switching those build steps off, not changing the site.

## What the site reads at runtime (all stored — no keys)

| Source | What | Needs a key? |
|---|---|---|
| Google Sheets (9 shards) | 24.5 lakh titles, queried through the gviz endpoint | no |
| `data/curated_*.json` | 1,334 curated titles with cast, director, OTT | no |
| `data/imdb_details.json.gz` | cast, director, overview for the enriched IMDb rows | no |
| `data/imdb_posters.json` | poster URLs per IMDb id | no |
| `data/tvmaze.json` | seasons, episodes, network per series | no |
| `data/watch_providers.json` | Indian streaming platforms per title | no |
| `data/watch_order.json` | MCU / DC watch order | no |
| `data/tmdb_exports.json` | the TMDB id dump | no |

Nothing above calls out to a service. Opening the site with the network blocked to
`api.themoviedb.org`, `datasets.imdbws.com` and `files.tmdb.org` changes nothing.

## Before you disconnect — the checklist

1. **Let the rolling fetchers finish.**
   - `fetch_posters_tmdb.py` → posters
   - `fetch_tmdb_details.py` → cast / director / overview
   - `fetch_tvmaze.py` → seasons and episodes
   - `fetch_watch_providers.py` → Indian OTT per title
   Each is resumable and stores what it has after every few thousand lookups, so a partial run is
   never lost. Check the counts printed at the end of each run.

2. **Freeze a snapshot into the Sheet.**
   Run the backup and confirm the workbook carries every list:

   ```
   python3 scripts/make_backup.py --out data/filmiset-backup.xlsx
   ```

   It writes `Curated (all lists)`, `All Titles`, `Summary` and a `Data files` index — so the
   workbook alone documents what was collected.

3. **Put the workbook and the database in the Drive folder** (`Filmiset_Data`), alongside the
   sheet shards. Drive is the cold backup; it is never fetched by the browser.

4. **Disable the API steps.** In `.github/workflows/update-data.yml`, comment out (or delete):
   - `Posters for the IMDb rows (rolling, TMDB by IMDb id)`
   - `Metadata for the IMDb rows (cast, director, overview)`
   - `Watch providers — where each title streams in India (TMDB)`
   - `TMDB daily ID exports`
   - `Download + compress posters locally` (only needed while posters are being fetched)
   Keep the IMDb-ingest step only if you still want new releases picked up; otherwise disable it
   too and the workflow becomes a no-op.

5. **Remove the secret.** GitHub → Settings → Secrets and variables → Actions → delete
   `TMDB_API_KEY`. With the steps disabled nothing reads it, and deleting it makes that certain.

6. **Confirm.** Dispatch the workflow once more; it should finish with no TMDB/IMDb calls. Then
   open the site and check a film, a series and a natak.

## Why it keeps working afterwards

- The Sheets are ordinary Google Sheets. gviz is a public read endpoint, so no key, no quota and
  no billing is involved.
- Every enrichment file is a plain JSON in `data/`, committed to the repo. GitHub Pages serves it
  like any other file.
- The workflow is the only thing that ever needed keys. Disable it and the site is unchanged.

## If you later want to add more titles

Re-enable the single step you need, add the key back, run it once, then disable it again. The
fetchers all skip titles they already have, so re-running costs only what is new.
