# THE ONE PROMPT — every Indian region, every language, films and series

This is the single prompt to paste into Gemini. It covers all of India in one instruction: the
batching rule is inside the prompt, so you only ever paste this once and then keep saying "next".

Paste everything in the box below, exactly as it is.

---

```
ROLE
You are compiling a structured reference document for a film and series database covering
the whole of India — every region, every language, every platform.

Deliver it as a PDF. The file is parsed by a script, so the format below is mandatory.

TITLE
"India Complete Entertainment Catalog — Part <N>: <regions in this part>"

────────────────────────────────────────────────────────────────
FORMAT RULES (mandatory — the parser depends on every one of them)
────────────────────────────────────────────────────────────────

1. Output ONLY tables, plus one heading line before each table. No commentary, no bullet
   points, no prose between rows, no footnotes, no closing remarks.

2. Every table has EXACTLY these four columns, in this order:
       Title & Year | Director / Creator | Primary Cast | Platform / Genre

3. One row per title. Put the year in brackets immediately after the title:
       Sholay (1975) | Ramesh Sippy | Amitabh Bachchan, Dharmendra, Hema Malini |
       Theatrical / Action Western
   For a series, give the first year only: Sacred Games (2018) | ...

4. Primary Cast: at most 4 names, comma separated. No character names, no "(voice)",
   no "(debut)". If you are unsure of the cast, write "—" rather than guessing.

5. Platform / Genre is written as "<platform> / <genre>".
   - Genre: 1-3 words only ("Political Crime Drama", not a sentence).
   - Platform: use ONLY these exact spellings —
       Netflix, Prime Video, JioHotstar, SonyLIV, ZEE5, Aha, Sun NXT, Hoichoi, MX Player,
       ShemarooMe, Chaupal, Planet Marathi, Ullu, AltBalaji, Eros Now, Lionsgate Play,
       Apple TV+, JioCinema, YouTube, Theatrical, Doordarshan, TV, Stage, Not streaming
   - "Theatrical" = cinema only. "Doordarshan"/"TV" = broadcast only. "Stage" = live plays.
     "Not streaming" = the title exists but is not available online.

6. Section headings go on their own line, numbered, before each table:
       1. Marathi Feature Films — Classic Era (1960-1999)
       2. Marathi Web Series
   Never start a table without a numbered heading line above it.

7. 40-100 rows per section. Many sections beats long sections.

8. NEVER INVENT A TITLE. A missing row is fine; a fabricated row is not. Accuracy over length.

────────────────────────────────────────────────────────────────
WHAT TO COVER — for EVERY region listed below
────────────────────────────────────────────────────────────────

Produce these sections for each region, skipping only the ones that genuinely do not exist:

   a. Feature films — classic era (pre-2000)
   b. Feature films — modern (2000-2026)
   c. Web series / OTT originals
   d. Short films
   e. Stage plays / nataks / theatre
   f. Documentaries and non-fiction

────────────────────────────────────────────────────────────────
REGIONS AND LANGUAGES — cover all of them, in this order
────────────────────────────────────────────────────────────────

  1. Hindi (Bollywood, Mumbai)
  2. Marathi (Maharashtra)
  3. Bengali (West Bengal)
  4. Tamil (Tamil Nadu)
  5. Telugu (Andhra Pradesh, Telangana)
  6. Malayalam (Kerala)
  7. Kannada (Karnataka)
  8. Punjabi (Punjab)
  9. Gujarati (Gujarat)
 10. Odia (Odisha)
 11. Assamese (Assam)
 12. Bhojpuri (Bihar, eastern UP)
 13. Urdu (pan-India, Hyderabad, Lucknow)
 14. Konkani (Goa)
 15. Nepali (Sikkim, Darjeeling)
 16. Sindhi (partition diaspora)
 17. Maithili (north Bihar)
 18. Manipuri (Manipur)
 19. Kashmiri (Jammu & Kashmir)
 20. Rajasthani / Marwari (Rajasthan)
 21. Haryanvi (Haryana)
 22. Chhattisgarhi (Chhattisgarh)
 23. Tulu (coastal Karnataka)
 24. Bodo (Bodoland, Assam)
 25. Santali (Jharkhand, Bengal, Odisha)
 26. Garhwali / Kumaoni (Uttarakhand)
 27. Dogri (Jammu)
 28. Khasi / Garo / Mizo (North-East)

────────────────────────────────────────────────────────────────
BATCHING — this is how the whole of India gets covered
────────────────────────────────────────────────────────────────

- Produce at most FOUR regions per PDF.
- Name each PDF: "India Complete Entertainment Catalog — Part 1: Hindi, Marathi, Bengali, Tamil"
  and continue Part 2, Part 3 … in the same order as the list above.
- After each PDF, STOP and wait for me to say "next". Do not continue on your own.
- When I say "next", produce the following four regions in exactly the same format,
  as a new PDF, and stop again.
- Keep going until all 28 regions are done.

────────────────────────────────────────────────────────────────
FINALLY, at the end of EVERY PDF
────────────────────────────────────────────────────────────────

Add one last section:
   "OTT & Platform Index"
with a two-column table:
   Platform | What it carries
listing every platform you used in that PDF, with one line on the kind of Indian content
each one holds.

BEGIN NOW with Part 1: Hindi, Marathi, Bengali, Tamil.
```

---

## How to run it

1. Paste the prompt. Gemini produces **Part 1** (Hindi, Marathi, Bengali, Tamil).
2. Send that PDF here — it becomes a parser run and a sheet append, like the Seven Canons did.
3. Reply to Gemini with **"next"**. It produces Part 2.
4. Repeat until all 28 regions are in. That is **7 PDFs** total.

## What each PDF becomes

| Step | What happens |
|---|---|
| You send the PDF | I extract the tables by word position (not by the PDF's table detector, which drops rows) |
| I parse it | title, year, director, cast, genre, platform per row |
| I categorise it | section number maps to a site category (Marathi, Regional Cinema, Documentaries …) |
| I append it | rows go into the Sheet shard, the site picks them up, CI verifies |

Nothing needs to be done by hand at any point.

## Why this prompt works when a generic one does not

- **Four fixed columns** — the parser reads the header to find column positions; a fifth column
  shifts everything.
- **Year in brackets** — that is how the year is extracted from the title cell.
- **`<platform> / <genre>`** — one cell fills both the OTT filter and the genre filter.
- **Closed list of platform spellings** — an unrecognised spelling becomes a dead filter chip.
- **Numbered section headings** — the section number decides the category and the type.
- **Four regions per PDF** — Gemini truncates long output, and a truncated table silently loses
  rows at the end.
- **"Stop and wait for next"** — keeps every batch the same shape, so one parser handles all 7.
