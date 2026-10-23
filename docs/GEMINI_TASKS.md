# What to give Gemini — and what to give Jules

Two different jobs, two different tools. Using the wrong one wastes the tool.

| | Gemini | Jules |
|---|---|---|
| **Good at** | knowing things, writing lists, translating, tagging | writing and fixing code, running repo chores |
| **Cannot do** | fetch 2.4M titles, query an API at speed | know film trivia, invent catalogue content |
| **Use it for** | curated lists, Hindi synopses, mood tags | scripts, tests, refactors, maintenance |

Neither can speed up bulk collection. That is an API-throughput problem, and it is already solved
by IMDb's own bulk files (`scripts/fetch_imdb_cast.py`) — one download instead of a million calls.

---

## 1. Gemini — paste this prompt to get more curated lists

The PDFs that produced 1,334 titles so far came from prompts like this. The important parts are
the **fixed column layout** (so the parser can read it) and **one table per section**.

```
Create a reference document as a PDF, in the same format as the Netflix Hindi Film Catalog
I sent earlier. Title it "<NAME> Master Catalog" with the subtitle
"Comprehensive Archive: <WHAT IT COVERS>".

Rules:
- Output ONLY tables plus a short intro line per section. No commentary between rows.
- Every table must have exactly these four columns, in this order:
     <Title> Title | <column 2> | <column 3> | <column 4>
  Use these headers per section type:
     for films/series:  Title & Year | Director / Creator | Primary Cast | Genre / Scale
     for stage plays:   Natak Title | Director / Troupe | Lead Cast | Genre / Tone
- One row per title. Put the year in brackets after the title: Ram Teri Ganga Maili (1985)
- Primary Cast: at most 4 names, comma separated, no roles in brackets.
- Genre / Scale: 1-3 words, e.g. "Political Crime Drama", not a sentence.
- Split into 4-6 sections (e.g. by era, by platform, by genre). Give each section a number
  and a heading like "1. ..." on its own line.
- Aim for 50-120 rows per section. More sections is better than more rows per section.
- Do not invent titles. If unsure of a title, leave it out.

Cover: <DESCRIBE EXACTLY WHAT YOU WANT — e.g. "Marathi theatre classics 1960-2020">
```

**Good requests to send next** (each becomes one PDF, one parser run, one sheet append):

- Marathi / Bengali / Tamil / Telugu / Punjabi / Malayalam cinema canons
- ZEE5, Aha, Sun NXT, Hoichoi, MX Player, Apple TV+ — deeper regional slates
- Era canons: 1950s-60s Indian cinema, 1970s parallel cinema, 1990s romance
- Genre canons: Indian horror, courtroom dramas, sports films, biopics, heist films
- Anime, K-drama, Turkish and Spanish series with official Hindi dubs
- Documentary and true-crime catalogues

## 2. Gemini — Hindi synopses (after collection is frozen)

The overviews in the repo are English. Ask Gemini to translate in batches of ~40 and return
strict JSON, which is what the pipeline expects:

```
Translate each synopsis below into natural Hindi (Devanagari). Keep proper nouns in Latin script.
Return ONLY a JSON object mapping the id to the translation, nothing else.

{"tt0111161": "<english synopsis>", "tt0068646": "<english synopsis>"}
```

## 3. Gemini — mood / theme tags

Genre alone cannot tell you whether a film is a rainy-day watch. Ask for tags in a fixed set so
they line up with the site's MOODS list:

```
For each title, choose at most 3 tags from exactly this list:
Feel-Good, Comedy, Romantic, Thriller, Mystery, Action, Emotional, Horror, Nostalgic, Family
Return JSON: {"tt0111161": ["Emotional", "Mystery"]}
```

---

## 4. Jules — code work, not data work

Jules is already wired in (`.github/workflows/jules-daily.yml`). Give it **bounded, checkable**
tasks. Good ones for this repo:

1. **Add a test for the parsers.** `scripts/fetch_imdb_cast.py`, `build_ott2.py` and the PDF
   parsers have no tests. Ask for a test that runs each parser against the sample input already in
   `docs/` and asserts the row count and the first row's title.
2. **Make the fetchers resumable everywhere.** `fetch_posters_tmdb.py` and
   `fetch_tmdb_details.py` checkpoint; confirm the others do too, and add the same pattern where
   they do not.
3. **Check the site against a missing data file.** Delete each `data/*.json` in turn and confirm
   the page still boots. Fix any `TypeError` on an undefined global.
4. **Deduplicate the PDF parsers.** There are five near-copies (`build_netflix3.py`,
   `build_ott2.py`, `build_ott3.py`, `build_ott4.py`, `build_ott5.py`). Ask for one parameterised
   parser plus a small config per catalogue.
5. **Verify the OTT links.** Walk `OTT_URL` in `index.html` and check every key is spelled the
   way the data spells it, so no card links to a Google search by accident.

Keep each Jules task to one file or one behaviour, and ask it to run `node --check` on
`index.html`'s script block before it finishes.
