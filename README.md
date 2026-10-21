# FilmiSet

Mood, language aur **"where to watch"** ke hisaab se movie discovery site.

Ek single-file static site — koi build step nahi, koi API key nahi. Catalog ek **Google Sheet** se aata hai.

## Categories
- Gujarati Movies
- Gujarati Natak
- Hindi
- South (Hindi Dubbed)
- English (Hindi Dubbed)
- Korean (Hindi Dubbed)

## Features
- Mood filters (Feel-Good, Comedy, Romantic, Thriller, Mystery, Action, Emotional, Horror, Nostalgic, Family)
- Type filter (Movie / Natak / Series) + live search
- Era filter (Classic pre-2000 / Modern) + a "Classic" badge on old titles
- Har title par: year, genres, mood tags, available audio (Hindi dub included), OTT platforms
- **"Where to watch"** button -> JustWatch India search (100% legal)

## Structure
```
index.html                 # the whole site (HTML + CSS + JS)
data/movies.json           # catalog, generated from the Google Sheet
scripts/sheet_to_json.py   # Google Sheet (Catalog tab) -> data/movies.json
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
     python3 scripts/sheet_to_json.py --url "https://docs.google.com/.../pub"
     ```
   - **Downloaded CSV:** `File -> Download -> CSV`, then
     ```
     python3 scripts/sheet_to_json.py --csv ~/Downloads/FilmiSet.csv
     ```
3. Commit the updated `data/movies.json`. The site picks it up automatically.

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
