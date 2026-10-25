# Working in this repository

This file is for AI agents and automated contributors — Jules, Copilot, and anyone else opening a
pull request here. Read it before you branch.

## The one rule that matters most

**Branch from the current `main`, and rebase before you open the pull request.**

```bash
git fetch origin
git checkout -b your-branch origin/main      # branch from origin/main, not a stale local main
# ... make your changes ...
git fetch origin && git rebase origin/main   # before opening the PR
```

Two pull requests here were opened from a base that was days old. Their `index.html` was around
70 KB while `main` had grown past 200 KB, so merging them would not have applied a fix — it would
have **reverted** everything merged since: the site's hosting URLs, the hero layout, the filter
panel, the data manifest, and a security fix. A stale branch is not a small problem when the file
it touches is the whole application.

If your branch is more than a day old, rebase it. If a rebase conflicts in `index.html`, do not
resolve it by taking your side wholesale — `main` is the truth, and your change is a small delta on
top of it.

## What this project is

FilmiSet — a free, non-commercial catalogue of films, series and Gujarati natak. Static HTML,
deployed from a private repository. The whole site is one file: `index.html`.

## Layout

| Path | What it is |
|---|---|
| `index.html` | The entire site — markup, styles and script in one file |
| `scripts/` | The data pipeline. Python, no framework |
| `data/` | JSON the site fetches at runtime |
| `.github/workflows/` | `update-data.yml` refreshes the catalogue weekly; `ci.yml` guards every push |

## Rules for changes

1. **Never commit a secret.** `ci.yml` runs gitleaks on every push and will fail the build.
2. **Keep `index.html` self-contained.** No build step, no bundler, no new runtime dependency. It
   is served as a static file and must stay that way.
3. **Escape anything that reaches `innerHTML`.** Every row passes through `sanitizeRow()` in
   `mergeSets()`; that is the funnel, and it exists because a title containing markup once executed
   script on the page. If you add a field, add it there too.
4. **Do not add `backdrop-filter` to repeated elements.** It was on every pill and button once —
   over 350 GPU layers on one screen — which made the site crawl and made Android paint the pills
   blank. Blur belongs on the large surfaces only.
5. **`esc()` is not optional and not cosmetic.** It escapes `&`, `<`, `>`, `"` and `'`, in that
   order. An earlier version replaced only double quotes, which is how the XSS got in.
6. **The data pipeline must run without any API key.** IMDb's bulk files, TVmaze and Wikidata need
   none. TMDB is used when `TMDB_API_KEY` is present and skipped cleanly when it is not. Nothing
   may hard-fail because a key is absent.
7. **Respect the Actions budget.** This repository is private, so it is limited to 2,000 minutes a
   month and the other repositories on this account already use about 1,500. The data refresh runs
   weekly for that reason. Do not add a schedule that runs more often.
8. **One concern per pull request**, and say in the description what you tested and what you
   could not.

## Before you open a pull request

- [ ] Branched from `origin/main` and rebased onto it
- [ ] `index.html` still parses: extract the `<script>` block and run `node --check`
- [ ] `python3 scripts/validate_data.py` passes
- [ ] No secret, no new dependency, no build step
- [ ] The description says what changed and how it was verified

## On `esc()` and security claims

If you believe you have found an injection, reproduce it first — construct the payload, put it
through the real code path, and show it executing. A claim of a vulnerability that cannot be
reproduced wastes everyone's time; a real one that is dismissed as a false positive is worse. The
XSS fixed here was reported, dismissed as unlikely, and turned out to be real.
