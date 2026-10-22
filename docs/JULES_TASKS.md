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
