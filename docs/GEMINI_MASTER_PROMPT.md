# The all-rounder Gemini prompt — India, every language, every platform

Paste the block below into Gemini. It is written so the output can be parsed directly into the
FilmiSet sheet — the column layout, the year-in-brackets rule and the numbered section headings
are all things the parser reads.

**How to use it**

1. Paste the prompt. Ask for **one PDF per 3-4 languages** (Gemini will not fit 25 languages in
   one document) — e.g. "now do the next 4 languages as a separate PDF".
2. Send each PDF here. Each one becomes a parser run and a sheet append.
3. Keep going until the language list is exhausted. Nothing needs to be done by hand.

---

## The prompt

```
You are building a structured reference document for a film database. Produce it as a PDF.

TITLE: "India Complete Entertainment Catalog — <LANGUAGES IN THIS FILE>"

FORMAT — follow this exactly, the file is parsed by a script:

1. Output ONLY tables plus one heading line per section. No commentary, no bullet points,
   no prose between rows, no footnotes.

2. Every table has exactly these FOUR columns, in this order:
       Title & Year | Director / Creator | Primary Cast | Platform / Genre

3. One row per title. Put the year in brackets immediately after the title:
       Sholay (1975) | Ramesh Sippy | Amitabh Bachchan, Dharmendra, Hema Malini |
       Theatrical / Action Western

4. Primary Cast: at most 4 names, comma separated. No character names, no "(voice)" notes.

5. Platform / Genre: write it as "<platform> / <genre>". Genre is 1-3 words only
   ("Political Crime Drama", not a sentence).
   Platform must be one of these exact spellings:
       Netflix, Prime Video, JioHotstar, SonyLIV, ZEE5, Aha, Sun NXT, Hoichoi, MX Player,
       ShemarooMe, Chaupal, Planet Marathi, Ullu, AltBalaji, Eros Now, Lionsgate Play,
       Apple TV+, YouTube, JioCinema, Theatrical, Doordarshan, TV, Stage, Not streaming
   Use "Theatrical" for cinema-only releases, "TV"/"Doordarshan" for broadcast-only,
   "Stage" for plays, and "Not streaming" when a title exists but is unavailable online.

6. Section headings go on their own line, numbered, like:
       1. Marathi Feature Films — Classic Era (1960-1995)
       2. Marathi Feature Films — Modern (2000-2026)
   Do not put a table directly against a heading without the heading line first.

7. 40-100 rows per section. More sections is better than longer sections.

8. DO NOT INVENT TITLES. If you are not confident a title exists, leave it out. Accuracy
   matters far more than length.

SECTIONS — for EACH language listed below, produce these sub-sections where they exist:
       a. Feature films — classic era (pre-2000)
       b. Feature films — modern (2000-2026)
       c. Web series / OTT originals
       d. Short films
       e. Stage plays / nataks
       f. Documentaries / non-fiction

LANGUAGES TO COVER — do all of them, in this order:
   1.  Hindi
   2.  Marathi
   3.  Bengali
   4.  Tamil
   5.  Telugu
   6.  Malayalam
   7.  Kannada
   8.  Punjabi
   9.  Gujarati
   10. Odia
   11. Assamese
   12. Bhojpuri
   13. Urdu
   14. Konkani
   15. Nepali
   16. Sindhi
   17. Maithili
   18. Manipuri
   19. Kashmiri
   20. Rajasthani
   21. Haryanvi
   22. Chhattisgarhi
   23. Tulu
   24. Bodo
   25. Santali

BATCHING: produce at most 4 languages per PDF. When I say "next", continue with the next
4 languages in the same format, as a new PDF with the same structure. Keep the same title
pattern: "India Complete Entertainment Catalog — <languages>".

FINALLY: end each PDF with one extra section called
       "OTT & Platform Index"
with a 2-column table:
       Platform | What it carries
listing every platform you used above, with one line on what kind of Indian content it holds.

Start now with languages 1-4 (Hindi, Marathi, Bengali, Tamil) and wait for me to say "next".
```

---

## Why the prompt is shaped this way

| Instruction | Why it is there |
|---|---|
| Exactly four columns | the parser splits on the header; five columns break the row banding |
| Year in brackets | that is how the year is detected per row |
| `<platform> / <genre>` | one cell feeds both the OTT filter and the genre filter |
| Fixed platform spellings | an unknown spelling shows up as a broken filter chip |
| Numbered section headings | section number decides the category and type |
| "Do not invent titles" | a hallucinated row is worse than a missing one — it cannot be caught |
| 4 languages per PDF | Gemini truncates long documents, and a truncated table loses rows |
| "wait for me to say next" | keeps every batch the same shape, so one parser run handles all of them |

## After the PDFs arrive

Each PDF is handled the same way as the Netflix, Prime, Hotstar, SonyLIV, ZEE5, Gujarati and
Multi-OTT catalogues: parse the tables, infer genre and mood, append to the Sheet, commit, verify
CI. Nothing further is needed from you.
