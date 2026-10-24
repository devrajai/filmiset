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

## About the disclaimer — what it can and cannot do

This is the part people get wrong, so it is worth being blunt.

**A disclaimer is not a licence.** It describes the position you are taking. It does not grant you
any right you did not already have. No wording — in any language, however carefully written —
turns "personal and non-commercial use only" into permission to sell something. If a rights holder
disagrees with you, a paragraph on your About page is not a defence; it is at best evidence of
good faith.

**What the disclaimer on this site does do, and does do usefully:**

| It does | Why it matters |
|---|---|
| States plainly that the project is free and non-commercial | This is the *only* thing that keeps the current setup defensible. It is also the honest description of what the site is today |
| Credits IMDb, TMDB, Wikidata and TVmaze by name | TMDB **requires** attribution. Without it you are in breach regardless of everything else |
| Says TMDB does not endorse or certify the site | The exact wording their terms ask for |
| Says the site is not affiliated with any platform | Stops a trademark complaint before it starts |
| Says nothing is hosted, streamed or downloaded here | Distinguishes a catalogue from a piracy site. This is the single most important line on the page |
| Says the data may be wrong and gives a correction route | Limits liability and satisfies the notice-and-takedown expectation |
| Offers removal on request | Shows good faith, and is usually enough to resolve a complaint quietly |

**What no disclaimer can do:**

- It cannot make commercial use of IMDb data legal. No licence for that exists at any price.
- It cannot remove the licence attached to copies already on disk.
- It cannot stop a takedown notice, a platform ban, or an ad network rejecting the site.
- It cannot convert TMDB's free tier into a commercial one. Only a paid plan does that.

So: keep the disclaimer, keep it accurate, and understand it as **a fair-dealing position for a
free site** — not as a workaround. The moment the site earns money, the disclaimer stops being the
relevant document and the licence becomes it again.

**The rule to remember:** a disclaimer protects a free project. A licence protects a paid one.
