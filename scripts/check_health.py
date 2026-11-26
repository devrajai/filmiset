#!/usr/bin/env python3
"""check_health.py — is the pipeline actually producing fresh data?

The workflows can all report success and still publish nothing. That happened for weeks: the fresh
pull built its file every morning and then could not commit it, because the workflow declared
contents: read — the run was green and the site had no new releases. A green tick is not evidence.

This checks the artefacts themselves rather than the runs: is each data file present, was it written
in the last day and a half, does it contain rows, and has the catalogue shrunk. Exit 1 on a problem so
the workflow goes red and the alert opens an issue.
"""
import datetime, gzip, json, os, sys

MAX_AGE_HOURS = 36
CHECKS = [
    ("data/fresh.json.gz",     "fresh releases"),
    ("data/calendar.json.gz",  "release calendar"),
    ("data/wd_new.json.gz",    "Wikidata titles"),
]
problems, notes = [], []


def age_hours(path):
    ts = datetime.datetime.utcfromtimestamp(os.path.getmtime(path))
    return (datetime.datetime.utcnow() - ts).total_seconds() / 3600


for path, label in CHECKS:
    if not os.path.exists(path):
        problems.append(f"{label}: {path} is missing")
        continue
    hours = age_hours(path)
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        problems.append(f"{label}: cannot read ({str(e)[:60]})")
        continue

    rows = 0
    if path.endswith("fresh.json.gz"):
        rows = len(d.get("cinema") or []) + len(d.get("upcoming") or [])
        for grp in ("ott", "series", "tvnow", "bylang"):
            rows += sum(len(v) for v in (d.get(grp) or {}).values())
    elif path.endswith("calendar.json.gz"):
        rows = sum(len(v.get("theatre") or []) + len(v.get("digital") or [])
                   for m in (d.get("months") or {}).values() for v in m.values())
    else:
        rows = len(d.get("items") or [])

    stamp = d.get("updated") or "?"
    if rows == 0:
        problems.append(f"{label}: file is empty")
    elif hours > MAX_AGE_HOURS:
        problems.append(f"{label}: last written {hours:.0f}h ago (limit {MAX_AGE_HOURS}h), stamp {stamp}")
    else:
        notes.append(f"{label}: {rows} rows, written {hours:.0f}h ago, stamp {stamp}")

# the catalogue: a rebuild that silently produced half the titles would still look green
man = "data/ix_manifest.json"
if os.path.exists(man):
    try:
        m = json.load(open(man, encoding="utf-8"))
        n = m.get("titles") or 0
        if n < 700000:
            problems.append(f"catalogue: only {n:,} titles — a rebuild has gone wrong")
        else:
            notes.append(f"catalogue: {n:,} titles in {len(m.get('buckets') or {})} buckets")
    except Exception as e:
        problems.append(f"catalogue manifest unreadable ({str(e)[:50]})")
else:
    problems.append("catalogue manifest is missing")

for x in notes:
    print(f"  OK   {x}")
for x in problems:
    print(f"  FAIL {x}")

if problems:
    print(f"\n{len(problems)} problem(s) — the pipeline is not producing fresh data")
    sys.exit(1)
print("\nall data files are present, recent and non-empty")
