# FilmiSet

Mood, language aur **"where to watch"** ke hisaab se movie discovery site.

Ek single-file static site — koi build step nahi, koi API key nahi. Browser mein `index.html` kholo, bas.

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
- Har title par: year, genres, mood tags, available audio (Hindi dub included), OTT platforms
- **"Where to watch"** button -> JustWatch India search (100% legal)

## Chalane ka tarika
```
# seedha browser mein kholo
index.html
```
Ya local server se:
```
python3 -m http.server 8000
# phir http://localhost:8000 kholo
```

## Data (demo)
Abhi ~40 titles ka **sample data** embedded hai (concept dikhane ke liye). Real version mein:
- **Titles / genres / language / posters** -> TMDB API (free key)
- **"Kahan dekho"** -> JustWatch / Streaming Availability API
- **Hindi-dubbed aur Gujarati-natak** ka data manually curate karna padega (koi API direct nahi deta)

## Roadmap
- [ ] TMDB API integration (serverless function se key chhupana)
- [ ] Gujarati natak + Hindi-dubbed curated CSV
- [ ] Festival / weekend curated sections
- [ ] Watchlist (localStorage)

## Legal
Saare watch-links legal OTT platforms (JioHotstar, Prime Video, Netflix, ShemarooMe, JOJO, MX Player) aur JustWatch search par le jaate hain.
**Koi piracy ya free-download link nahi.** Site kisi content ko host nahi karti — sirf availability dikhati hai.
