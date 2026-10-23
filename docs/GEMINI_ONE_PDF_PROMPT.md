# ONE prompt, ONE PDF, all of India

Paste this once. You get one PDF covering all 28 regions. No parts, no "next", no back-and-forth.

## The honest limit, and how this works around it

Gemini can fit roughly **250 rows** in one PDF. All of India, split into six content types per
region, would be about **1,700 rows** — that cannot fit in one document, whatever the prompt says.

So this prompt does something different: **one section per region, about 10 rows each**, mixing
that region's most important films, series, shorts, plays and documentaries. 28 × 10 = **280 rows
= one PDF**, with every region represented.

What that means in practice: you get the **top 10 of every region** in one file. Deeper lists per
region can come later if you want them — but this single PDF covers the whole country.

## The prompt — copy this

```
Make ONE PDF titled "India Complete Entertainment Catalog — All Regions".

ABSOLUTE RULES
1. Tables ONLY. No cover page, no intro, no summary, no notes, no conclusion.
   Nothing but numbered headings, tables and page numbers.
2. Every table has EXACTLY 4 columns:
   Title & Year | Director / Creator | Primary Cast | Type · Platform / Genre
3. Year in brackets after the title: Sholay (1975). Series: first year only.
4. Cast: max 4 names, comma separated, or "—" if unknown.
5. 4th column is exactly: "<Type> · <Platform> / <Genre>"
   Type — one of: Feature Film, Web Series, Short Film, Stage Play, Documentary
   Platform — one of: Netflix, Prime Video, JioHotstar, SonyLIV, ZEE5, Aha, Sun NXT,
     Hoichoi, MX Player, ShemarooMe, Chaupal, Planet Marathi, Ullu, AltBalaji, Eros Now,
     Lionsgate Play, Apple TV+, JioCinema, YouTube, Theatrical, Doordarshan, TV, Stage,
     Not streaming
   Genre — 1-3 words.
   Example:  Web Series · Netflix / Crime Drama

SECTIONS — one numbered section per region, in this exact order:
1 Hindi    2 Marathi   3 Bengali   4 Tamil     5 Telugu    6 Malayalam  7 Kannada
8 Punjabi  9 Gujarati  10 Odia     11 Assamese 12 Bhojpuri 13 Urdu      14 Konkani
15 Nepali  16 Sindhi   17 Maithili 18 Manipuri 19 Kashmiri  20 Rajasthani 21 Haryanvi
22 Chhattisgarhi 23 Tulu 24 Bodo 25 Santali 26 Garhwali/Kumaoni 27 Dogri 28 Khasi/Garo/Mizo

Give EACH region 10 rows — its most important Feature Films, Web Series, Short Films,
Stage Plays and Documentaries, mixed. Mark which is which in the 4th column.

TOTAL: 28 sections, about 280 rows, in ONE PDF. Do not split into parts.
Use a compact layout — one line per row, no blank lines — so everything fits.

NEVER INVENT A TITLE.

If you truly cannot fit all 28, end with exactly:
RESUME AT: SECTION <n>
```

## What happens when you send the PDF

| Step | Who |
|---|---|
| Paste the prompt, get one PDF | you + Gemini |
| Send the PDF here | you |
| Parse all 28 sections, read the type and platform from the 4th column | me |
| Append to the Sheet, add any new categories, commit, verify CI | me |

The parser reads `Web Series · Netflix / Crime Drama` and splits it into type, platform and
genre — so a single four-column table carries everything the site's filters need.

## If you want more than 10 rows per region later

Say so and I will give you a prompt scoped to a handful of regions at a time, which is the only
way to go deeper — the PDF limit is on Gemini's side, not ours.
