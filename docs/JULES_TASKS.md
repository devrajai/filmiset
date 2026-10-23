# FilmiSet — task brief for an AI coding agent (Jules)

## What this repo is

**FilmiSet** is a free, static movie & web-series discovery website. Everything is plain
HTML/CSS/JS — there is **no build step, no framework, no npm**. GitHub Pages serves it from
the `main` branch root.

- Live site: https://devrajai.github.io/filmiset/
- Repo: https://github.com/devrajai/filmiset

### Files that matter

| Path | What it is |
|---|---|
| `index.html` | The **entire website** — HTML + CSS + JS in one self-contained file. Almost every UI task happens here. |
| `data/catalog.json` | Main catalogue (Wikidata) — ~1660 titles. Rewritten daily by the Action. |
| `data/tmdb.json` | TMDB discover rows (trending / popular / per-language). |
| `data/jikan.json` | Anime source (currently empty — the API is unreachable from CI). |
| `data/movies.json` | Hand-curated titles. |
| `data/youtube.json` | YouTube channel videos — **knowledge only, never shown in the feed**. |
| `data/tmdb_cache.json` | TMDB enrichment cache (OTT, runtime, rating, age-cert, trailer, summary, cast, director). |
| `posters/` | ~2900 compressed local posters (300 px JPEG q70). |
| `scripts/*.py` | The free data pipeline (stdlib + pillow + openpyxl only). |
| `.github/workflows/update-data.yml` | Daily 02:30 UTC job: fetch → enrich → localise posters → build backup → commit. |
| `data/filmiset-backup.xlsx` | Excel backup (Readme / All Titles / Summary), refreshed by the Action. |

### Title object shape (fields you can rely on)

```json
{
  "t": "Title", "y": 2010, "date": "2010-07-31",
  "cat": "hindi|gujarati-movie|south-dubbed|english-dubbed|korean-dubbed|anime|animation",
  "type": "Movie|Series|Natak", "cats": ["anime","animation"],
  "g": ["Drama","Romance"], "m": ["Emotional","Romantic"], "a": ["Hindi (dub)","Korean"],
  "o": ["Netflix","Prime Video"], "poster": "posters/x.jpg", "src": "wikidata|tmdb|jikan|youtube",
  "status": "released|upcoming", "pop": 139, "franchise": "Marvel Cinematic Universe",
  "rt": 132, "rtg": 7.4, "vot": 1200, "cert": "UA", "irt": 8.1, "ivot": 250000,
  "ov": "Short plot summary…", "cast": ["Actor A","Actor B"], "dir": "Director", "prod": "Studio",
  "tr": "YouTubeVideoId", "imdb": "tt1234567"
}
```

## Hard rules — do not break these

1. **No piracy.** Never add or link torrent/streaming-pirate sources. Watch links go to legal
   platforms or a JustWatch search only.
2. **No secrets in `index.html`.** The TMDB key lives only in the GitHub Actions secret
   `TMDB_API_KEY` and is read by `scripts/fetch_tmdb*.py`. Never hardcode a key anywhere.
3. **Keep `index.html` a single self-contained file.** No bundler, no CDN framework, no npm.
   Small inline SVG/CSS is fine. External fonts already come from Google Fonts.
4. **`node --check` must pass** on the `<script>` block after every edit.
5. **Mobile first.** The filter rail becomes a bottom-sheet on phones; keep that working.
6. **UI copy is Hinglish** ("Kya dekhein?", "Aaj ka vibe", "Mark seen"). Keep that tone.
7. **Don't reformat or "modernise" unrelated code** — small, reviewable diffs only.
8. **`src: "youtube"` rows must never appear in the feed** (they are internal knowledge only).

## Tasks

### T1 — PWA: installable + offline
Add `manifest.webmanifest` (name "FilmiSet", short_name "FilmiSet", `display: standalone`,
theme/background colours matching the site, 192 px + 512 px icons — reuse the existing "F"
logo as an inline SVG-generated PNG or a simple SVG icon), link it from `index.html`, and add
a small service worker (`sw.js`) that caches the shell (`index.html`, `data/*.json`) with a
cache-first-then-network strategy and a versioned cache name. Register it only on `https:`.
Show a small "Install app" button when `beforeinstallprompt` fires.
**Done when:** Lighthouse reports the PWA installable criteria met, and the site still loads
with the network offline after one visit.

### T2 — Gujarati / Hinglish UI toggle
Add a language toggle in the top bar with two states: **Hinglish (default)** and **ગુજરાતી**.
Put every user-visible string in a single `I18N` object at the top of the script
(`{hinglish:{...}, gujarati:{...}}`) and render labels through a `t(key)` helper. Persist the
choice in `localStorage` and reflect it in the URL (`?lang=gu`). Translate at minimum: hero
title + subtitle, every filter section heading, every filter pill label, the result count,
card actions ("Mark seen", "More like this", "▶ Trailer"), the detail window buttons, the
empty state and the "Load more" button. Do **not** translate movie titles.
**Done when:** switching language re-renders the whole UI without a reload and no English
string remains in the Gujarati mode except titles/genres.

### T3 — Instagram-style share card
On each card and in the detail window add a **Share card** button that draws a 1080×1080
`<canvas>`: the poster (cover-cropped) on top, then title, year, IMDb/TMDB rating, genre
chips and the site URL on a solid brand background, with a small "FilmiSet" wordmark.
Export with `canvas.toBlob()` and share via `navigator.share({files:[...]})` when available,
otherwise download the PNG. Handle missing posters with a colour-block fallback.
**Done when:** the downloaded PNG is exactly 1080×1080 and legible at phone size.

### T4 — Weather-based picks (Open-Meteo, no key)
Ask for location only on an explicit button click (`navigator.geolocation`), then call
`https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&current=temperature_2m,weather_code`.
Map the weather code to a mood: rain → Romantic/Emotional, clear+hot → Feel-Good/Comedy,
cloudy → Mystery/Thriller, cold → Family. Show one pick in the "Aaj ka vibe" strip with the
weather line (e.g. "Barish hai — cozy romance?"). Cache the result for 30 minutes. If the user
denies location, hide the feature silently.
**Done when:** the vibe strip shows a weather-aware pick after granting location, and nothing
breaks when location is denied.

### T5 — Festival / holiday auto-detection (Nager.Date, no key)
Call `https://date.nager.at/api/v3/PublicHolidays/{year}/IN` at boot. If today (or the next 7
days) is an Indian public holiday, highlight the matching occasion pills (Diwali, Holi,
Independence Day, Eid, Christmas, New Year, Navratri…) and pin a small "Aaj <festival> hai"
banner above the grid. Fall back to the existing hard-coded occasion list when the API fails.
**Done when:** the site degrades gracefully offline and the banner appears on a holiday.

### T6 — Award badges (Wikidata)
Extend `scripts/fetch_data.py` to also read `wdt:P166` (award received) for each title, keep
the top 1–2 human-readable awards, store them as `"aw": ["National Film Award","Filmfare Award"]`,
and render a small gold badge on the card plus a line in the detail window. Awards must be
filtered to a known allow-list so we don't show noise.
**Done when:** the daily Action writes `aw` and the badge appears only for winners.

### T7 — Giscus comments
Add a collapsible "Comments" section to the detail window that loads
`https://giscus.app/client.js` with the repo's own `data-repo="devrajai/filmiset"`,
`data-mapping="specific"` and a per-title term (the title name), `data-theme` matched to the
site's light/dark state. Load it lazily — only when the section is opened — so it costs
nothing until used. Make the repo/`repo-id`/`category` easy to fill in with a clearly marked
TODO block.
**Done when:** comments load per title only after the section is expanded.

### T8 — Analytics (GoatCounter, free)
Add a single deferred `<script data-goatcounter="https://YOURCODE.goatcounter.com/count" async src="//gc.zgo.at/count.js">`
with a clearly marked TODO for the code, and fire named events on: filter applied, Surprise
me, Mark seen, Trailer click, detail window open. Never send the user's search text.
**Done when:** events fire in the console stub when `data-goatcounter` is unset (no errors).

### T9 — Group vote
Add a "Vote with friends" button that builds a shareable link containing up to 5 title names
(URL-encoded, `?vote=Title1|Title2|…`). Opening that link shows a small voting panel where
each friend taps a title; votes are stored in `localStorage` per link and the tally is shown
with the user's own pick highlighted. No backend, no accounts.
**Done when:** two browser profiles can each vote on the same link and see their own tally.

### T10 — Suggest a title
Add a "Suggest a title" link in the footer that opens a pre-filled Google Form
(`https://docs.google.com/forms/d/e/…/viewform?usp=pp_url&entry.XXXX=…`) with the current
search text passed through when present. Leave the form ID as a clearly marked TODO.
**Done when:** the link opens the form with the search text pre-filled.

### T11 — Grow the catalogue (data pipeline)
In `.github/workflows/update-data.yml` raise the TMDB discover depth from `--pages 1` to
`--pages 5`, and in `scripts/fetch_tmdb_discover.py` add more Indian languages
(`as`, `or`, `ur`, `ne`, `sa`) to `LANGS` plus a `--min-votes` filter so junk is excluded.
Keep the whole job under ~45 minutes: if poster localisation becomes the bottleneck, raise
`download_posters.py` workers to 4 and skip posters for rows whose `vote_count` is 0.
**Done when:** the catalogue grows to roughly 8–12k titles and the job still finishes green.

### T12 — Polish
- Keyboard access: cards focusable, `Enter` opens the detail window, `Esc` closes it.
- `aria-label` on every icon-only button; visible focus rings.
- Lazy-load posters (`loading="lazy"` already present — verify) and add `decoding="async"`.
- Keep the whole page under ~250 KB of HTML+CSS+JS.
- Add a `<meta name="description">` and Open Graph tags so shared links look good.

## How to verify your work

1. `python3 - <<'EOF'` … extract the `<script>` block from `index.html` and run
   `node --check` on it — it must pass.
2. Open `index.html` in a headless browser at 390×844 (phone) and 1280×900 (desktop) and
   confirm: the grid renders, filters apply, a card click opens the detail window, and no
   console errors appear.
3. For data changes, run the script locally against a small sample and confirm the JSON keys
   match the shape documented above.
4. Never commit a broken `data/*.json` — the site reads them at boot and a parse error blanks
   the grid.

## Please do NOT

- Add npm/webpack/vite, React/Vue, or any build step.
- Put API keys, tokens or credentials in any file.
- Add piracy, torrent or unofficial streaming links.
- Rewrite `index.html` wholesale — make targeted, reviewable edits.
- Show `src: "youtube"` rows in the feed.

---

# Second wave (T13 – T25)

### T13 — Deep-linkable title pages + Open Graph
Give every title a stable URL: `?t=<slug>` (slug = lowercase title + year, e.g. `3-idiots-2009`).
Opening it boots the site with that title's detail window already open. Add a `<link rel="canonical">`
and update `og:title` / `og:description` / `og:image` dynamically when a title opens, so
WhatsApp/Instagram previews show the poster and summary. Wire the browser back button
(`pushState` / `popstate`) so Back closes the window instead of leaving the site.
**Done when:** pasting `?t=…` opens that title, Back closes it, and the og tags reflect the title.

### T14 — "Trending in India" + "New this week on OTT"
Two horizontally scrolling rows above the grid, each hidden when empty:
- **Trending** — a new `scripts/fetch_trending.py` pulling TMDB `/trending/{movie,tv}/week?region=IN`
  into `data/trending.json` (uses `TMDB_API_KEY`, fail-safe, always writes a file).
- **New this week on OTT** — titles that have a non-empty `o` and a release date within 7 days.
**Done when:** both rows render and simply disappear when their data is missing.

### T15 — Sort + view options
Extend Sort to: Newest · Most popular · **Top rated (IMDb)** · **A–Z** · **Shortest first**.
Add a grid / list toggle (list = compact rows: thumbnail, title, year, rating, OTT).
Persist both in the URL (`?sort=`, `?view=list`).
**Done when:** every sort produces a visibly different, correct order and the view survives reload.

### T16 — Search upgrade
Debounced (150 ms) autocomplete showing the top 6 matches, searching across **title, cast,
director, studio and genre** (all already in the data). Highlight the matched substring in the
results. Keyboard: ↑/↓ to move, Enter to open the highlighted title.
**Done when:** typing `khan` surfaces titles with "Khan" in the cast, and Enter opens the pick.

### T17 — Watchlist export / import + Recently viewed
Add **Export** (download `filmiset-watchlist.json`) and **Import** (file picker → merge + dedupe)
to the Saved view, plus a **Recently viewed** row (last 12 opened titles, `localStorage`, with a
clear button).
**Done when:** export → clear → import restores the exact watchlist.

### T18 — Accessibility pass (WCAG AA)
Everything reachable by Tab with a visible focus ring; `aria-label` on every icon-only button;
the detail window is a real dialog (`role="dialog"`, `aria-modal`, focus trapped, `Esc` closes,
focus returns to the card that opened it); body-text contrast ≥ 4.5:1 in both themes; the mobile
filter drawer announces open/closed state.
**Done when:** a keyboard-only user can operate every feature and an axe-core scan reports no
critical issues.

### T19 — Performance budget
Skeleton placeholders while the JSON loads, `preload` for `data/catalog.json`, defer non-critical
work, first render under 1.5 s on a throttled 3G profile, and total HTML+CSS+JS under 250 KB
(posters excluded).
**Done when:** Lighthouse performance ≥ 90 on mobile.

### T20 — CI guard so nothing can silently break the site
New `.github/workflows/ci.yml` on every push/PR that: (a) extracts the `<script>` from
`index.html` and runs `node --check`; (b) validates every `data/*.json` parses and each row has
the required keys (`t`, `cat`, `type`, `g`, `m`, `a`, `o`); (c) fails if a poster path referenced
in the JSON is missing from `posters/`. This protects future agent changes.
**Done when:** a deliberately broken JSON on a test branch turns the check red.

### T21 — Attribution & privacy panel
A small "About & credits" panel reachable from the footer: TMDB attribution
("This product uses the TMDB API but is not endorsed or certified by TMDB"), plus IMDb, Wikidata,
Jikan and JustWatch credits, and a plain-language privacy note (everything is stored locally,
analytics is anonymous, no accounts, no tracking).
**Done when:** the panel opens and names every data source.

### T22 — SEO & feeds
`robots.txt`, a `sitemap.xml` generated by the Action from the catalogue (cap at 5 000 URLs) and a
`feed.xml` of the latest 50 additions so people can subscribe.
**Done when:** the sitemap lists real titles and the feed validates.

### T23 — Poster storage strategy
Add a size guard to the pipeline: when `posters/` passes ~800 MB, stop growing it — shrink new
JPEGs to 240 px / q65 and skip posters for rows with `vote_count < 5`. Document how to move
posters to a CDN or Drive if it is ever needed.
**Done when:** the guard is implemented and the repo stays inside GitHub's soft limits.

### T24 — "♪ Songs" button
No free API lists per-movie songs, so add a **♪ Songs** button on the card and in the detail window
that opens a YouTube search for `"<title> <year> songs"` in a new tab. Keep it visually separate
from the trailer button.
**Done when:** the button opens a correctly pre-filled YouTube search.

### T25 — More languages & regions
Add `as, or, ur, ne, sa, bn, mr, pa` to the language discovery in `fetch_tmdb_discover.py`, and add
a region switch for OTT data (`IN` / `US` / `GB`) so the "Available on…" line can show a second
region's platforms.
**Done when:** the new languages appear with sensible Category labels and the region switch changes
the OTT line.

---

# Third wave (T26 – T36) — after the Google Sheet shards and the daily cron

Context you must know before starting: the catalogue now lives in **9 public Google Sheets**
(see `data/sheet_shards.json` and `docs/SCALE.md`). A weekly agent cron syncs them. The site
queries the shards live through the Google **gviz** endpoint (CORS is allowed, and it supports
server-side SQL: `tq=select A,B,C,E,G,H where B contains 'x' order by H desc limit 20`).
`data/imdb_indian.json` holds the most-voted Indian titles and `data/imdb_posters.json` maps
`tconst -> poster URL`.

### T26 — Verify and repair every OTT link
`OTT_URL` in `index.html` maps a platform name to its **search** URL. Several of these were
guessed and were never verified. Check each one against the real site, correct the ones that
are wrong, and make `ottLink()` fall back to the platform home page (not a broken search path)
when a title is empty. Add a short comment listing which ones you verified.
**Done when:** every platform in the map opens a working page for a real title.

### T27 — "Popular in India" row
Add a horizontally scrolling row above the grid that shows the most-voted **Indian** titles
from `data/imdb_indian.json` (fall back to the shards with `order by H desc` when the file is
missing). Hide the row when there is nothing to show. Give each card the existing card markup
so Save / Mark seen / More like this keep working.
**Done when:** the row renders with real Indian titles and disappears gracefully offline.

### T28 — Search across cast, director and studio
The local rows carry `cast`, `dir` and `prod`. Extend the search box to match those too and
show the matched field on the card (e.g. "Cast: …"). Keep the live sheet search working
alongside it.
**Done when:** typing an actor or director name returns their titles, and typing a title still works.

### T29 — Keep the page fast now that it loads more
The boot now also fetches the shard manifest, the poster map and the popular rows. Add
skeletons while those load, keep the first render under 1.5 s on a throttled connection, and
make sure the poster map is only fetched once. Total HTML+CSS+JS must stay under 250 KB.
**Done when:** Lighthouse performance ≥ 90 on mobile and no layout jump when posters arrive.

### T30 — Accessibility pass (WCAG AA)
Keyboard access everywhere, `aria-label` on icon-only buttons, the detail window is a real
dialog (`role="dialog"`, `aria-modal`, focus trapped, `Esc` closes, focus returns to the card),
contrast ≥ 4.5:1 in both themes, and the mobile filter drawer announces its state.
**Done when:** an axe-core scan reports no critical issues and the site is fully usable by keyboard.

### T31 — Giscus comments on each title
Lazy-load `https://giscus.app/client.js` in the detail window with `data-repo="devrajai/filmiset"`
and a per-title term, `data-theme` matched to the site's light/dark state. Only load it when the
section is expanded. Leave the `repo-id` / `category` values as clearly marked TODOs.
**Done when:** comments load per title only after expanding the section.

### T32 — Anonymous analytics (GoatCounter)
Add the deferred GoatCounter script with a TODO for the code, and fire named events for:
filter applied, Surprise me, Mark seen, Trailer click, detail window open, live sheet search.
Never send the user's search text.
**Done when:** events fire without errors when the GoatCounter code is still unset.

### T33 — Instagram-style share card
A **Share card** button (card + detail window) that draws a 1080×1080 canvas: poster, title,
year, rating, genre chips and the site URL, then shares via `navigator.share({files})` or
downloads the PNG. Handle missing posters with a colour block.
**Done when:** the exported PNG is exactly 1080×1080 and legible on a phone.

### T34 — Gujarati / Hinglish UI toggle
A language toggle (Hinglish default, ગુજરાતી) driven by a single `I18N` object and a `t(key)`
helper. Persist in `localStorage` and reflect it in the URL (`?lang=gu`). Translate the hero,
every filter heading and pill, card actions, the detail window buttons, the empty state and
"Load more". Do **not** translate titles.
**Done when:** switching re-renders the whole UI with no reload and no English left in Gujarati mode.

### T35 — Guard the sheet shards in CI
Extend `scripts/validate_data.py` (run by `.github/workflows/ci.yml`) to also fetch
`data/sheet_shards.json`, and for each shard confirm the sheet id/tab still respond on the gviz
endpoint and that the row count is within 5% of the manifest. Fail the check with a clear
message when a shard has been deleted, renamed or emptied.
**Done when:** a deliberately wrong sheet id in the manifest turns CI red.

### T36 — Replaces the manual sheet sync with a real job
The weekly cron currently does the sheet sync by hand. Write `scripts/sync_sheets.py` plus a
workflow that appends any new rows from `data/imdb_all.json.gz` / `data/tmdb_full.json.gz` into
the shards using a **Google service account** (`GOOGLE_SA_JSON` repo secret), keeping every
sheet under Google's 20,000,000-cell limit, and updates the MASTER INDEX
(`1ZonhzqGrArw0aISB9lgeY04MJ5YIJJDsBEOj7UIMn5c`). Document the one-time service-account setup
in `docs/SCALE.md`. If the secret is missing the script must exit 0 and change nothing.
**Done when:** the job appends new titles without any manual step and the master index updates itself.
