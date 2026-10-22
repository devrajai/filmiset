#!/usr/bin/env python3
"""validate_data.py — guard the catalogue so a bad commit can never blank the site.

Checks, for every data file the website loads at boot:
  * it exists and is valid JSON, and its top level is a list
  * every row is an object carrying the keys the site relies on
  * every poster path a row points at actually exists on disk

Run by .github/workflows/ci.yml on every push and pull request.

    python3 scripts/validate_data.py
"""
import json, os, sys

FILES = [
    "data/catalog.json", "data/tmdb.json", "data/jikan.json",
    "data/movies.json", "data/youtube.json",
]
REQUIRED = ("t", "cat", "type", "g", "m", "a", "o")
LIST_TYPES = ("g", "m", "a", "o")


def main():
    errors, missing, total = [], set(), 0

    for f in FILES:
        if not os.path.exists(f):
            print(f"  {f}: not present (skipped)")
            continue
        try:
            rows = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            errors.append(f"{f}: not valid JSON ({type(e).__name__}: {e})")
            continue
        if not isinstance(rows, list):
            errors.append(f"{f}: top level must be a list, got {type(rows).__name__}")
            continue
        print(f"  {f}: {len(rows)} rows")
        for i, r in enumerate(rows):
            total += 1
            if not isinstance(r, dict):
                errors.append(f"{f}[{i}]: row is not an object")
                continue
            label = r.get("t") or f"row {i}"
            for k in REQUIRED:
                if k not in r:
                    errors.append(f"{f}[{i}] ({label}): missing key {k!r}")
            for k in LIST_TYPES:
                if k in r and not isinstance(r[k], list):
                    errors.append(f"{f}[{i}] ({label}): {k!r} must be a list")
            p = r.get("poster") or ""
            if isinstance(p, str) and p.startswith("posters/") and not os.path.exists(p):
                missing.add(p)

    if missing:
        sample = ", ".join(sorted(missing)[:5])
        errors.append(f"{len(missing)} referenced poster file(s) missing from posters/ — e.g. {sample}")

    if errors:
        print("\nFAILED:")
        for e in errors[:40]:
            print("  -", e)
        if len(errors) > 40:
            print(f"  … and {len(errors) - 40} more")
        print(f"\n{len(errors)} problem(s) found")
        return 1

    print(f"\nOK — {total} rows validated across {len(FILES)} data files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
