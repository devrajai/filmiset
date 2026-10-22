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


def rows_for(movies):
    out = []
    for i, m in enumerate(movies, start=1):
        out.append([
            i, m.get("t", ""), m.get("y", ""), m.get("date", ""),
            CAT_LABEL.get(m.get("cat"), m.get("cat", "")), m.get("type", ""),
            ", ".join(m.get("g") or []), ", ".join(m.get("m") or []),
            ", ".join(m.get("a") or []), ", ".join(m.get("o") or []),
            m.get("src", ""), m.get("status", "released"),
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
    cols = ["#", "Title", "Year", "Release date", "Category", "Type", "Genres", "Moods",
            "Audio", "OTT Platforms", "Source", "Status", "Poster file"]
    widths = [6, 34, 7, 13, 22, 8, 24, 22, 20, 26, 10, 11, 34]
    ws = wb.create_sheet("Catalog")
    ws.sheet_properties.tabColor = NAVY
    header(ws, cols, widths)
    write_rows(ws, rows_for(catalog))

    tw = wb.create_sheet("TMDB")
    tw.sheet_properties.tabColor = "01B4E4"
    header(tw, cols, widths)
    write_rows(tw, rows_for(tmdb_rows))

    jw = wb.create_sheet("Anime (MyAnimeList)")
    jw.sheet_properties.tabColor = "2E51A2"
    header(jw, cols, widths)
    write_rows(jw, rows_for(jikan_rows))

    ws2 = wb.create_sheet("Curated")
    ws2.sheet_properties.tabColor = GOLD
    header(ws2, cols, widths)
    write_rows(ws2, rows_for(curated))

    # --- YouTube ---
    yc = ["#", "Title", "Channel", "Category", "Published", "Video URL", "Full video title"]
    yw = [6, 34, 22, 20, 13, 40, 60]
    ys = wb.create_sheet("YouTube")
    ys.sheet_properties.tabColor = "C4302B"
    header(ys, yc, yw)
    yrows = []
    for i, v in enumerate(youtube, start=1):
        yrows.append([i, v.get("t", ""), v.get("channel", ""),
                      CAT_LABEL.get(v.get("cat"), v.get("cat", "")),
                      v.get("date", ""), v.get("trailer", ""), (v.get("note") or "")[:200]])
    write_rows(ys, yrows)

    # --- OTT summary ---
    counter = collections.Counter()
    for m in catalog + curated + tmdb_rows + jikan_rows:
        for p in (m.get("o") or []):
            counter[p] += 1
    osheet = wb.create_sheet("OTT Summary")
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
    wb.save(args.out)
    print(f"wrote {args.out}: catalog={len(catalog)} tmdb={len(tmdb_rows)} anime={len(jikan_rows)} "
          f"curated={len(curated)} youtube={len(youtube)} ott-tagged={total}")


if __name__ == "__main__":
    main()
