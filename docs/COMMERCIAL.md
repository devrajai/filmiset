# Going commercial — what has to change, and what cannot

Read this before switching on ads, a subscription, or anything else that earns money.

## The short version

**You cannot use the data you already have for a commercial product.** Not because of a technical
limit — because of the licences the data arrived under.

| Source | Licence | Commercial? |
|---|---|---|
| IMDb bulk datasets (`datasets.imdbws.com`) | "personal and non-commercial use" | **No** |
| TMDB API (free tier) | non-commercial | **No** |
| TMDB API (commercial plan) | paid, applied for | Yes |
| **Wikidata** | **CC0** | **Yes, freely** |
| Wikipedia text | CC BY-SA | Yes, with attribution + share-alike |
| TVmaze | CC BY-SA | Yes, with attribution |
| Your own curated rows | yours | Yes |

So "drop IMDb and TMDB, go commercial" is not a thing you can do — the moment you earn from the
site, the data underneath it becomes the problem, and dropping the *sources* does not drop the
*licence* that is attached to the copies already on disk.

## The three honest routes

### Route A — stay free, stay grey
Keep the site free. Keep the attribution. Add a plain line: "FilmiSet is a free, non-commercial
project. Title and rating data comes from IMDb and TMDB; this site is not endorsed by either."
Most hobby sites do exactly this. It is not a licence, it is a defensible position, and it is
where you are today. Nothing to do.

### Route B — commercial on free-and-open data only (recommended)
Rebuild the data layer from sources that permit commercial use, and earn from the result.

```
DROP        IMDb bulk datasets        (no commercial licence exists at any price)
REPLACE     with  TMDB commercial plan  — paid, but it is the only real OTT-availability source
            or    Wikidata CC0          — free, commercial-safe, thinner coverage
KEEP        Wikipedia + TVmaze          — commercial OK with attribution
KEEP        your own curated rows       — 100% yours, and the part nobody can copy
```

What this costs you: **posters and OTT coverage drop**, because Wikidata has neither as deeply as
TMDB. What it buys you: **you can charge money without a lawyer in the room.**

### Route C — licence the data properly
Apply for the TMDB commercial plan (they grant it, it is priced per use), drop IMDb entirely, and
keep everything else. This is the cleanest path and the only one that keeps OTT availability at
full strength. Budget for it before you budget for anything else.

## What is actually yours, and is worth money

Be clear-eyed about this. The titles, years, ratings and posters are not yours and never will be.
These are:

- **The curated rows** — ~2,866 hand-checked titles, the regional lists, the natak, the situations.
- **The mood tags and the 91 situation mappings** — judgement, not data.
- **The Vakeel wording, the talk-about questions, the one-line lessons.**
- **The "talk to the site" word list** that reads Hinglish.
- **The engine** — regret risk, fit over fame, honest skip.

That is the product. The rest is raw material, and raw material can be bought by anyone.

## Practical checklist before the first rupee

```
[ ] Decide the route (A, B or C) — write it down, this is a business decision not a code one
[ ] If B or C: apply for the TMDB commercial plan FIRST, before building on it
[ ] Remove every IMDb-sourced column (ratings, votes, runtime) or replace them
[ ] Keep every attribution line that a remaining source requires
[ ] Add a real Terms page and a Privacy page (analytics, if you add any, must be declared)
[ ] Do not describe the site as "IMDb ratings" anywhere once IMDb data is gone
[ ] Keep the report-wrong-info form — it is also your correction policy
[ ] Re-check the poster URLs: TMDB images stay up, but check their terms for commercial display
[ ] If you add OTT affiliate links, label them, and never let them change the ranking
```

## The one-line rule

**Free: keep the data, keep the attribution. Commercial: change the data, or buy the licence.**
There is no third option, and no amount of re-collecting changes which licence a file arrived under.
