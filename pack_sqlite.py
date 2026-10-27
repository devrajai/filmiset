#!/usr/bin/env python3
"""
pack_sqlite.py — run the same packer over our SQLite database instead of a CSV.

pack_data.py reads CSV. The Filmiset master database is SQLite, with 12.8M rows of which most are
episodes. This wraps the same packing logic so it can read the DB directly, works out the column
names instead of assuming them, and drops the rows a suggestion site cannot use.

    python3 pack_sqlite.py filmiset_all_world_master_15m.db out_dir
    python3 pack_sqlite.py --selftest 200000 out_test      # no database needed

What it drops, and why — this is where most of the size goes:
  episodes          an episode belongs under its series; it is not a title you suggest
  no votes at all   a row nobody has rated cannot be ranked, and the engine ranks by rating
  adult             not what the site is for

What it keeps: every real title, with the columns the packer needs. Overviews and cast are not in
this database, so the detail packs will be empty — those come from TMDB separately.

Column names: the DB was built by a Colab script, so the exact names are not guaranteed. This looks
for the usual candidates and prints what it found before doing any work.
"""
import argparse, os, sqlite3, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from pack_data import pack, CORE_N, LANG_PAGE, PACKS
except ImportError:
    print("pack_data.py must sit next to this file"); sys.exit(1)


def find_col(cols, *names):
    """Match a column name case-insensitively, and accept the usual aliases."""
    low = {c.lower(): c for c in cols}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None


def detect(cur):
    cols = [r[1] for r in cur.execute("PRAGMA table_info(all_world_media)")]
    print("columns found:", cols)
    m = {
        "id":       find_col(cols, "imdb_id", "tconst", "id"),
        "title":    find_col(cols, "title", "primaryTitle", "t", "name"),
        "year":     find_col(cols, "year", "startYear", "y"),
        "type":     find_col(cols, "type", "titleType", "kind"),
        "language": find_col(cols, "language", "lang", "primaryLanguage"),
        "votes":    find_col(cols, "votes", "numVotes", "num_votes"),
        "rating":   find_col(cols, "rating", "averageRating", "avg_rating"),
        "genres":   find_col(cols, "genres", "genre", "g"),
        "runtime":  find_col(cols, "runtime", "runtimeMinutes", "minutes"),
    }
    # Only id and title are truly required. Everything else has a safe default, because the
    # column names in this database are not guaranteed and a missing genre column should not stop
    # the whole run.
    print("mapping:", m)
    missing = [k for k in ("id", "title") if not m[k]]
    if missing:
        print("could not find:", missing)
        print("available columns were:", cols)
        print("edit detect() and name them explicitly, then run again")
        sys.exit(1)
    for k in ("year", "type", "language", "votes", "rating", "genres", "runtime"):
        if not m[k]:
            print("  no %s column — using a default" % k)
    return m, cols


def rows_from_db(db, limit=None):
    con = sqlite3.connect(db)
    cur = con.cursor()
    m, cols = detect(cur)
    has_type = bool(m["type"])
    has_votes = bool(m["votes"])
    has_adult = bool(find_col(cols, "adult", "isAdult"))

    where = []
    if has_type:
        where.append("lower(coalesce(%s,'movie')) NOT IN ('episode','tvepisode')" % m["type"])
    if has_votes:
        where.append("coalesce(%s,0) > 0" % m["votes"])
    if has_adult:
        where.append("coalesce(%s,0) = 0" % find_col(cols, "adult", "isAdult"))
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    DEFAULTS = {"year": "0", "type": "'movie'", "language": "'und'",
                "votes": "0", "rating": "0", "genres": "''", "runtime": "0"}
    sel = ", ".join(
        "%s AS %s" % (m[k] or DEFAULTS[k], k) for k in
        ("id", "title", "year", "type", "language", "votes", "rating", "genres", "runtime"))
    q = "SELECT %s FROM all_world_media %s" % (sel, clause)
    if limit:
        q += " LIMIT %d" % limit
    print("\nquery:", q)
    t0 = time.time()
    n = 0
    for row in cur.execute(q):
        n += 1
        if n % 500000 == 0:
            print("  read %d rows (%.0fs)" % (n, time.time() - t0), flush=True)
        yield dict(zip(("id", "title", "year", "type", "language", "votes", "rating",
                        "genres", "runtime"), row))
    print("  read %d rows total in %.0fs" % (n, time.time() - t0))


def fake_rows(n, seed=7):
    """Same fake generator as pack_data, so the two paths can be compared."""
    from pack_data import fake_rows as fr
    return fr(n, seed)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("db", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--selftest", nargs=2, metavar=("N", "OUT"))
    ap.add_argument("--limit", type=int, default=None, help="only the first N rows (for a test run)")
    a = ap.parse_args()

    if a.selftest:
        n, out = int(a.selftest[0]), a.selftest[1]
        print("selftest with %d fake titles -> %s" % (n, out))
        man, sizes = pack(fake_rows(n), out)
    elif a.db and a.out:
        if not os.path.exists(a.db):
            print("no such database:", a.db); sys.exit(1)
        print("reading", a.db, "->", a.out)
        man, sizes = pack(rows_from_db(a.db, a.limit), a.out)
    else:
        print(__doc__); sys.exit()

    total = sum(sizes.values())
    print("\ntitles:", man["titles"], "| languages:", len(man["languages"]),
          "| search shards:", man["searchShards"])
    print("sizes (MB):", {k: round(v / 1e6, 1) for k, v in sizes.items()},
          "| TOTAL %.1f MB" % (total / 1e6))
    print("\nUpload the output folder to your data host, then point the loader at it.")
