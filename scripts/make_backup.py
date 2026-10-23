#!/usr/bin/env python3
"""make_backup.py — write a full backup of the catalogue to an Excel workbook.

    python3 scripts/make_backup.py --out data/filmiset-backup.xlsx

Sheets:
  Readme       what this file is + how it is generated
  Catalog      every title (from Wikidata) with its OTT platforms
  Curated      the hand-curated Google Sheet titles
  YouTube      videos collected from the YouTube channels
  OTT Summary  how many titles each platform has
"""
import argparse, json, os, collections

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FONT = "Arial"
NAVY = "1F3A5F"
GOLD = "B8761A"
thin = Side(style="thin", color="D8CFC0")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

CAT_LABEL = {
    "gujarati-movie": "Gujarati Movies", "gujarati-natak": "Gujarati Natak",
    "hindi": "Bollywood", "south-dubbed": "South - Hindi Dubbed",
    "english-dubbed": "Hollywood", "korean-dubbed": "Korean - Hindi Dubbed",
    "anime": "Anime", "animation": "Animation",
}


def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return []


def header(ws, cols, widths):
    for i, (c, w) in enumerate(zip(cols, widths), start=1):
        cell = ws.cell(row=1, column=i, value=c)
        cell.font = Font(name=FONT, bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 26
    ws.freeze_panes = "A2"


SRC_LABEL = {"wikidata": "Wikidata", "tmdb": "TMDB", "jikan": "MyAnimeList", "youtube": "YouTube"}


def rows_for(movies, default_src=""):
    out = []
    for i, m in enumerate(movies, start=1):
        out.append([
            i, m.get("t", ""), m.get("y", ""), m.get("date", ""),
            CAT_LABEL.get(m.get("cat"), m.get("cat", "")), m.get("type", ""),
            ", ".join(m.get("g") or []), ", ".join(m.get("m") or []),
            ", ".join(m.get("a") or []), ", ".join(m.get("o") or []),
            m.get("irt", ""), m.get("rt", ""), m.get("cert", ""), m.get("rtg", ""),
            SRC_LABEL.get(m.get("src"), default_src or m.get("src") or "Curated sheet"),
            m.get("status", "released"),
            (m.get("poster") or "").replace("posters/", ""),
        ])
    return out


def write_rows(ws, rows):
    for r in rows:
        ws.append(r)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for c in row:
            c.font = Font(name=FONT, size=10)
            c.border = BORDER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/filmiset-backup.xlsx")
    ap.add_argument("--catalog", default="data/catalog.json")
    ap.add_argument("--movies", default="data/movies.json")
    ap.add_argument("--youtube", default="data/youtube.json")
    ap.add_argument("--tmdb", default="data/tmdb.json")
    ap.add_argument("--jikan", default="data/jikan.json")
    args = ap.parse_args()

    catalog = load(args.catalog)
    curated = load(args.movies)
    youtube = load(args.youtube)
    tmdb_rows = load(args.tmdb)
    jikan_rows = load(args.jikan)

    wb = Workbook()

    # --- Readme ---
    rd = wb.active
    rd.title = "Readme"
    rd.column_dimensions["A"].width = 3
    rd.column_dimensions["B"].width = 30
    rd.column_dimensions["C"].width = 78
    rd["B1"] = "FilmiSet — data backup"
    rd["B1"].font = Font(name=FONT, size=15, bold=True, color=NAVY)
    info = [
        ("What is this", "A backup of everything the FilmiSet website shows."),
        ("Catalog sheet", f"{len(catalog)} titles auto-collected from Wikidata (free, no API key)."),
        ("TMDB sheet", f"{len(tmdb_rows)} titles from TMDB discover (trending / popular / per-language)."),
        ("Anime sheet", f"{len(jikan_rows)} anime from Jikan (MyAnimeList, free)."),
        ("Curated sheet", f"{len(curated)} hand-curated titles (from the Google Sheet)."),
        ("YouTube sheet", f"{len(youtube)} videos collected from the YouTube channels."),
        ("Total titles", f"{len(catalog) + len(tmdb_rows) + len(jikan_rows) + len(curated)} across all sources."),
        ("OTT Platforms", "Filled from TMDB watch-provider data (India) where available."),
        ("Regenerate", "python3 scripts/make_backup.py  (runs daily in the GitHub Action)"),
        ("Website", "https://devrajai.github.io/filmiset/"),
    ]
    r = 3
    for k, v in info:
        rd.cell(row=r, column=2, value=k).font = Font(name=FONT, size=11, bold=True)
        rd.cell(row=r, column=3, value=v).font = Font(name=FONT, size=11)
        r += 1

    # --- Catalog ---
    cols = ["#", "Title", "Year", "Release date", "Category", "Type", "Franchise", "Genres", "Moods",
            "Audio", "OTT Platforms", "IMDb", "Runtime", "Age cert", "TMDB rating", "Source", "Status", "Poster file"]
    widths = [6, 34, 7, 13, 22, 8, 22, 24, 22, 20, 26, 8, 9, 10, 12, 15, 11, 34]
    ws = wb.create_sheet("All Titles")
    ws.sheet_properties.tabColor = NAVY
    header(ws, cols, widths)
    write_rows(ws, rows_for(catalog + tmdb_rows + jikan_rows + curated + youtube))

    # --- OTT summary ---
    counter = collections.Counter()
    for m in catalog + curated + tmdb_rows + jikan_rows:
        for p in (m.get("o") or []):
            counter[p] += 1
    osheet = wb.create_sheet("Summary")
    header(osheet, ["OTT Platform", "Titles"], [28, 10])
    total = sum(1 for m in catalog + curated + tmdb_rows + jikan_rows if m.get("o"))
    for p, n in counter.most_common():
        osheet.append([p, n])
    osheet.append(["—", "—"])
    osheet.append(["Titles with OTT info", total])
    alln = len(catalog) + len(curated) + len(tmdb_rows) + len(jikan_rows)
    osheet.append(["Titles without OTT info", alln - total])
    osheet.append(["—", "—"])
    osheet.append(["Source", "Titles"])
    for name, n in (("Wikidata", len(catalog)), ("TMDB", len(tmdb_rows)),
                    ("MyAnimeList (Jikan)", len(jikan_rows)), ("Curated sheet", len(curated)),
                    ("YouTube", len(youtube))):
        osheet.append([name, n])
    osheet.append(["TOTAL", alln])
    for row in osheet.iter_rows(min_row=2, max_row=osheet.max_row):
        for c in row:
            c.font = Font(name=FONT, size=10)
            c.border = BORDER

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    # --- every curated list, merged into one sheet ---
    import glob
    cur = wb.create_sheet("Curated (all lists)")
    header(cur, ["List", "Title", "Year", "Type", "Category", "Genres", "Audio", "OTT",
                 "Director", "Cast", "Overview"], [22, 34, 7, 8, 15, 22, 16, 18, 24, 34, 50])
    lists_seen = []
    n_cur = 0
    for f in sorted(glob.glob("data/curated_*.json")):
        rows = load(f)
        if not rows:
            continue
        label = os.path.basename(f)[len("curated_"):-len(".json")]
        lists_seen.append((label, len(rows)))
        for m in rows:
            if not isinstance(m, dict) or not m.get("t"):
                continue
            n_cur += 1
            cur.append([label, m.get("t"), m.get("y"), m.get("type"), m.get("cat"),
                        ", ".join(m.get("g") or []), ", ".join(m.get("a") or []),
                        ", ".join(m.get("o") or []), m.get("dir") or "",
                        ", ".join((m.get("cast") or [])[:5]), (m.get("ov") or "")[:400]])
    cur.freeze_panes = "A2"

    # --- an index of every data file, so nothing is silently left out ---
    idx = wb.create_sheet("Data files")
    header(idx, ["File", "Rows", "Size (KB)", "What it holds"], [34, 10, 11, 62])
    NOTES = {
        "catalog.json": "titles auto-collected from Wikidata",
        "tmdb.json": "titles from TMDB discover",
        "jikan.json": "anime from MyAnimeList (Jikan)",
        "imdb_all.json.gz": "every IMDb title with rating + votes (the sheet shards)",
        "imdb_stats.json": "counts from the IMDb ingest",
        "imdb_top.json": "the 30,000 most-voted IMDb titles",
        "imdb_indian.json": "Indian titles from the IMDb akas file",
        "imdb_posters.json": "poster URLs per IMDb id (TMDB)",
        "sheet_shards.json": "manifest of the Google Sheet shards",
        "watch_order.json": "MCU / DC in-universe watch order",
        "tvmaze.json": "seasons, episodes and network per series (TVmaze)",
        "watch_providers.json": "Indian streaming platforms per title (TMDB)",
        "tmdb_exports.json": "TMDB daily ID exports",
        "curated_*.json": "hand-curated lists (see the Curated sheet)",
    }
    for f in sorted(glob.glob("data/*")):
        if os.path.isdir(f):
            continue
        base = os.path.basename(f)
        kb = round(os.path.getsize(f) / 1024, 1)
        if base.endswith(".json"):
            rows = load(f)
            n = len(rows) if isinstance(rows, list) else (len(rows.get("shards", [])) if isinstance(rows, dict) else "")
        else:
            n = ""
        note = NOTES.get(base, NOTES.get("curated_*.json" if base.startswith("curated_") else "", ""))
        idx.append([base, n, kb, note])

    # --- Readme gains the real totals ---
    rd.cell(row=r + 0, column=2)
    extra = r + len(info) + 2
    rd.cell(row=extra, column=2, value="Curated lists").font = Font(name=FONT, size=11, bold=True)
    rd.cell(row=extra, column=3, value=f"{n_cur} titles across {len(lists_seen)} lists: "
             + ", ".join(f"{a} ({b})" for a, b in lists_seen))

    wb.save(args.out)
    print(f"wrote {args.out}: catalog={len(catalog)} tmdb={len(tmdb_rows)} anime={len(jikan_rows)} "
          f"curated={len(curated)} youtube={len(youtube)} ott-tagged={total}")


if __name__ == "__main__":
    main()
