# The dense prompt — maximum rows per PDF, no truncation

Gemini stops at roughly 6-7 pages when the answer has prose in it. Compare:

| | Pages | Rows |
|---|---|---|
| Earlier PDFs (cover page + intro + notes) | 6-7 | ~107 |
| Part 1 (tables only) | **13** | **213** |

The difference is entirely the prose. Every paragraph Gemini writes is space it cannot spend on
rows. So this prompt bans prose outright and adds a resume marker for the rare case where it still
runs out of room.

Paste the box below. Then just keep saying **"next"**.

---

```
TASK
Build a structured catalogue of Indian entertainment for a film database. Output a PDF.

════════════════════════════════════════════════════════════
THE ONE RULE THAT MATTERS MOST: NO PROSE
════════════════════════════════════════════════════════════
Do NOT write: a cover page, a title page, an introduction, a summary, a methodology note,
a "how to read this", a legend, a statistics block, a closing remark, a conclusion, or any
sentence that is not a table heading or a table row.

The document must contain NOTHING but:
    - numbered section headings
    - tables
    - page numbers

Every other line you write costs rows and will be discarded. If you feel like explaining
something, do not. Fill the pages with rows instead.

════════════════════════════════════════════════════════════
TABLE FORMAT — mandatory, a script parses this
════════════════════════════════════════════════════════════
Every table has EXACTLY four columns, in this order:

    Title & Year | Director / Creator | Primary Cast | Platform / Genre

- Year in brackets right after the title:  Sholay (1975)
- Series get the first year only:          Sacred Games (2018)
- Cast: at most 4 names, comma separated. No character names. If unknown, write "—".
- Platform / Genre is "<platform> / <genre>", genre 1-3 words.
  Platform must be exactly one of:
    Netflix, Prime Video, JioHotstar, SonyLIV, ZEE5, Aha, Sun NXT, Hoichoi, MX Player,
    ShemarooMe, Chaupal, Planet Marathi, Ullu, AltBalaji, Eros Now, Lionsgate Play,
    Apple TV+, JioCinema, YouTube, Theatrical, Doordarshan, TV, Stage, Not streaming

════════════════════════════════════════════════════════════
SECTION HEADINGS
════════════════════════════════════════════════════════════
Numbered, on their own line, immediately above their table:

    1. HINDI FEATURE FILMS — CLASSIC ERA (PRE-2000)
    2. HINDI FEATURE FILMS — MODERN (2000-2026)
    3. HINDI WEB SERIES & OTT ORIGINALS
    4. HINDI SHORT FILMS
    5. HINDI STAGE PLAYS & THEATRE
    6. HINDI DOCUMENTARIES & NON-FICTION

Then repeat the same six for the next language, continuing the numbering (7, 8, 9 …).

════════════════════════════════════════════════════════════
HOW MUCH TO WRITE — this is the point of the prompt
════════════════════════════════════════════════════════════
- Produce 4 languages per PDF, 6 sections each = 24 sections.
- Target 200-250 rows in total, and do not stop early. Keep going until you have used
  the full length available to you.
- Aim for at least 8-12 rows per section even for the thinner ones (shorts, plays,
  documentaries). Never write "few titles exist" — write the ones that do.
- Use a compact table layout: one line per row wherever possible, no blank line between
  rows, small font. Density matters more than visual polish.

════════════════════════════════════════════════════════════
IF YOU RUN OUT OF ROOM — the resume marker
════════════════════════════════════════════════════════════
Stop cleanly at the END of a completed row. Never stop mid-row. Then, as the very last line
of the document, write exactly:

    RESUME AT: SECTION <n> — <heading text> — AFTER "<last title you wrote>"

Example:
    RESUME AT: SECTION 15 — BENGALI WEB SERIES & OTT ORIGINALS — AFTER "Byomkesh"

When I reply "continue", start a new PDF at exactly that point and carry on in the same
format. Do not repeat rows you already wrote.

════════════════════════════════════════════════════════════
LANGUAGES — one PDF covers four, in this order
════════════════════════════════════════════════════════════
  Part 1:  Hindi, Marathi, Bengali, Tamil
  Part 2:  Telugu, Malayalam, Kannada, Punjabi
  Part 3:  Gujarati, Odia, Assamese, Bhojpuri
  Part 4:  Urdu, Konkani, Nepali, Sindhi
  Part 5:  Maithili, Manipuri, Kashmiri, Rajasthani
  Part 6:  Haryanvi, Chhattisgarhi, Tulu, Garhwali / Kumaoni
  Part 7:  Bodo, Santali, Dogri, Khasi / Garo / Mizo

Name each file:  "India Complete Entertainment Catalog — Part <N>: <languages>"

════════════════════════════════════════════════════════════
ACCURACY
════════════════════════════════════════════════════════════
NEVER INVENT A TITLE. A missing row is acceptable. A fabricated row is not — it cannot be
detected later and it damages the catalogue. If you are unsure a title exists, leave it out
and add a different one you are sure about.

════════════════════════════════════════════════════════════
BEGIN
════════════════════════════════════════════════════════════
Produce Part 1 now: Hindi, Marathi, Bengali, Tamil — 24 sections, 200-250 rows, tables only.
Then stop and wait for me to say "continue".
```

---

## Why this gets more rows

| Rule | Effect |
|---|---|
| **No prose at all** | this alone roughly doubled the rows per PDF (107 → 213) |
| **No cover page / stats block** | the earlier PDFs spent a whole page on decorative headers |
| **"Use the full length available"** | Gemini stops early by default; this tells it not to |
| **Compact layout, one line per row** | more rows per page |
| **Minimum rows for thin sections** | stops it skipping shorts/plays with "few exist" |
| **RESUME marker** | if it does run out of room, nothing is lost — you say "continue" and it picks up exactly there |

## The workflow

1. Paste the prompt → **Part 1** PDF.
2. If the last line says `RESUME AT: ...`, reply **"continue"** to get the rest as another PDF.
3. Send every PDF here. Each is parsed and appended to the Sheet automatically.
4. When a part finishes cleanly (no RESUME line), reply **"next part"** to move on.

That is 7 parts, and each part may take 1-3 PDFs depending on how much it packs in.
