# Jules — the brief

Read this before every task. It is the whole context you need: what this project is, where things
live, what the rules are, and what is actually worth doing.

---

## What this is

**FilmiSet** — a free, non-commercial catalogue of films, web series and Gujarati natak, browsed by
mood. It answers "what should I watch tonight", not "what is popular".

| | |
|---|---|
| **Site** | https://filmiset.vercel.app |
| **Repository** | private |
| **Hosting** | Vercel, deployed from this repository on every push to `main` |
| **The whole site** | one file — `index.html` |
| **Data pipeline** | `scripts/`, run by GitHub Actions |
| **Refresh** | **weekly**, Mondays 08:00 IST — not daily, see the budget below |

---

## The rules, in order of how much they matter

### 1. Branch from the current `main`, and rebase before opening the pull request

```bash
git fetch origin
git checkout -b your-branch origin/main
# ... your change ...
git fetch origin && git rebase origin/main
```

This is first because it already went wrong twice. Two pull requests were opened from a base days
old, with `index.html` around 70 KB while `main` had passed 200 KB. Merging them would not have
applied a small fix — it would have reverted the hosting URLs, the hero layout, the filter panel,
the data manifest, the removal of the Saved button, and a security fix. When the file you touch is
the entire application, a stale branch is a destructive change dressed up as a small one.

If a rebase conflicts in `index.html`, `main` wins. Your change is a small delta on top of it.

### 2. The Actions budget

This repository is **private**, which means 2,000 Actions minutes a month instead of unlimited, and
the other repositories on this account already use about 1,500. That leaves roughly 500.

The data refresh runs weekly for exactly this reason. Do not add a schedule that runs more often,
and do not leave a workflow on a daily cron. If you need something to happen more often, say so in
your pull request rather than scheduling it.

### 3. Escape everything that reaches `innerHTML`

There is a single funnel: every row from every source — curated JSON, TMDB, Jikan, IMDb and the
Google Sheet — passes through `mergeSets()`, and `sanitizeRow()` cleans it there. If you add a
field that gets rendered, add it to `sanitizeRow()` too.

`esc()` escapes `&`, `<`, `>`, `"` and `'`, in that order. An earlier version replaced only double
quotes, which is how a title containing markup came to execute script on the page. If you change
`esc()`, know that you are changing the site's only line of defence.

URLs go through `safeUrl()`, because escaping the text around a `javascript:` URL does not stop it
executing.

### 4. No `backdrop-filter` on repeated elements

It was once on every pill and button — over 350 GPU layers on one screen. It made the site crawl
and it made Android paint the pills blank. Blur belongs on the large surfaces: the header, the
filter sheet, the modal, the talk panel. Nowhere else.

### 5. No secrets, no build step, no new dependencies

`ci.yml` runs gitleaks on every push. `index.html` is served as a static file and must stay
self-contained — no bundler, no framework, no npm. If your change needs a build step, it is the
wrong change.

### 6. The pipeline must run without any API key

IMDb's bulk files, TVmaze and Wikidata need none. TMDB is used when `TMDB_API_KEY` is present and
skipped cleanly when it is not. Nothing may hard-fail because a key is absent, and nothing may
report success while quietly doing nothing — that is how three data files stayed empty for days
while every run showed a green tick.

### 7. One concern per pull request

And say in the description what you changed, what you tested, and what you could not test.

---

## Where things live

| Path | What it is |
|---|---|
| `index.html` | The entire site. Markup, styles and script, one file |
| `AGENTS.md` | The same rules as above, shorter |
| `scripts/` | The data pipeline — plain Python, no framework |
| `data/` | JSON the site fetches at runtime |
| `docs/` | Notes, prompts and this brief |
| `.github/workflows/update-data.yml` | Weekly data refresh |
| `.github/workflows/ci.yml` | Guards every push: parses, validates, scans for secrets |
| `.github/workflows/jules-daily.yml` | This agent, weekly |
| `.github/workflows/jules-security.yml` | The security pass, weekly |

### Data shapes worth knowing

- A catalogue row: `{t, y, cat, type, g[], m[], a[], o[], poster, ov, status, cert, dir, cast[]}`
- `g` genres, `m` moods, `a` audio languages, `o` OTT platforms
- `cat` maps into `CATS` for the label and colour; always fall back if it is unknown
- The poster map is keyed by IMDb id and may arrive plain or gzipped

---

## What is actually worth doing

Work in this order. Stop when you have done one thing well.

1. **Fix what is broken.** If CI is red, or a file the site fetches is missing, fix that first and
   say so. Nothing else matters until the site works.
2. **Small, real improvements** to the reading experience: a clearer empty state, a faster first
   paint, a better mobile layout, a missing accessibility label.
3. **Data quality** — a wrong OTT platform, a duplicate row, a year that contradicts the title.

### Do not

- Do not add features nobody asked for. The list of ideas is long and the priority is not yours.
- Do not restructure `index.html` into modules, or introduce a build step.
- Do not "fix" the hero heading, its size or its centring unless the task is about that. It has been
  adjusted many times and it is measured correct.
- Do not touch the licence or non-commercial wording.
- Do not open a pull request that is mostly formatting.
- Do not claim a security issue without reproducing it. Construct the payload, run it through the
  real code path, and show it executing. The XSS in this repository was reported, dismissed as
  unlikely, and turned out to be real — so reproduce, but also do not cry wolf.

---

## Reporting back

In the pull request description:

```
What changed:      one or two sentences
Why:               the problem it solves
Tested:            what you actually ran, and what you saw
Not tested:        what you could not check, and why
Risk:              what could break, and how to undo it
```

If you could not do the task, say so plainly and explain what blocked you. A clear "I could not do
this, here is why" is worth far more than a pull request that quietly changes the wrong thing.
