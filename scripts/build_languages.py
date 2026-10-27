#!/usr/bin/env python3
"""build_languages.py — give every title a language, and its original-script name.

The master database has no language column, so every title lands under "und" and the site cannot
offer a language filter. It also has no native-script name, so a Tamil or Hindi reader searching in
their own script finds nothing, because IMDb stores the romanised title.

Both are in IMDb's title.akas file, which lists every alternate title a film has ever been released
under, with the region and the language for each. This reads it and writes two things:

  data/lang.json.gz         id -> language code, for the filter
  data/native.json.gz       id -> the title in its own script, for search

Both are single files rather than per-title packs, because the site needs them for every result it
shows, not one at a time. They are gzipped and columnar to stay small.

    python3 build_languages.py --akas title.akas.tsv.gz --catalogue data --out data
"""
import argparse, csv, glob, gzip, io, json, os, re, sys, time

def open_maybe_gz(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", newline="")
    return open(path, encoding="utf-8", newline="")

def norm_id(t):
    t = (t or "").strip()
    if t.startswith("tt") and t[2:].isdigit():
        t = t[2:]
    return str(int(t)) if t.isdigit() else t

# IMDb uses two-letter language codes in akas, and a few odd ones
LANG_NAMES = {
    "hi": "Hindi", "en": "English", "ta": "Tamil", "te": "Telugu", "ml": "Malayalam",
    "kn": "Kannada", "bn": "Bengali", "gu": "Gujarati", "mr": "Marathi", "pa": "Punjabi",
    "or": "Odia", "as": "Assamese", "ur": "Urdu", "ne": "Nepali", "si": "Sinhala",
    "ko": "Korean", "ja": "Japanese", "zh": "Chinese", "cn": "Chinese", "yue": "Cantonese",
    "fr": "French", "es": "Spanish", "de": "German", "it": "Italian", "pt": "Portuguese",
    "ru": "Russian", "ar": "Arabic", "fa": "Persian", "tr": "Turkish", "th": "Thai",
    "id": "Indonesian", "ms": "Malay", "vi": "Vietnamese", "tl": "Filipino", "he": "Hebrew",
    "pl": "Polish", "nl": "Dutch", "sv": "Swedish", "da": "Danish", "no": "Norwegian",
    "fi": "Finnish", "cs": "Czech", "hu": "Hungarian", "ro": "Romanian", "el": "Greek",
    "uk": "Ukrainian", "sr": "Serbian", "hr": "Croatian", "bg": "Bulgarian", "sw": "Swahili",
    "af": "Afrikaans", "is": "Icelandic", "et": "Estonian", "lv": "Latvian", "lt": "Lithuanian",
}

def is_native(s):
    """True when the string contains a script that is not Latin."""
    return bool(re.search(r'[\u0900-\u0DFF\u0A00-\u0AFF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF\u0590-\u05FF\u0600-\u06FF\u0400-\u04FF]', s or ""))

def catalogue_ids(data_dir):
    ids = set()
    for p in glob.glob(os.path.join(data_dir, "ix_*.json.gz")):
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                d = json.load(f)
            for v in d.get("i", []):
                ids.add(str(v))
        except Exception:
            continue
    return ids

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--akas", default="title.akas.tsv.gz")
    ap.add_argument("--catalogue", default="data")
    ap.add_argument("--out", default="data")
    a = ap.parse_args()

    if not os.path.exists(a.akas):
        print(f"missing {a.akas}"); sys.exit(1)

    t0 = time.time()
    print("reading the catalogue…")
    ship = catalogue_ids(a.catalogue)
    if not ship:
        print("no catalogue ids — run the packer first"); sys.exit(1)
    print(f"  {len(ship):,} ids")

    print("reading title.akas…")
    lang = {}
    native = {}
    n = 0
    with open_maybe_gz(a.akas) as f:
        r = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in r:
            tid = norm_id(row.get("titleId"))
            if tid not in ship:
                continue
            n += 1
            code = (row.get("language") or "").strip().lower()
            region = (row.get("region") or "").strip().upper()
            title = (row.get("title") or "").strip()
            is_orig = (row.get("isOriginalTitle") or "0").strip() == "1"

            # the language: prefer the original title's language, then any Indian release, then any
            if code and code in LANG_NAMES:
                prev = lang.get(tid)
                score = (2 if is_orig else 1) + (1 if region in ("IN", "PK", "BD", "LK", "NP") else 0)
                if prev is None or score > prev[0]:
                    lang[tid] = (score, code)

            # the native name: any alternate title in a non-Latin script
            if title and is_native(title) and tid not in native:
                native[tid] = title
    print(f"  {n:,} akas rows matched")
    print(f"  {len(lang):,} titles got a language")
    print(f"  {len(native):,} titles have a native-script name")

    # columnar, keyed by id
    lang_out = {k: v[1] for k, v in lang.items()}
    with gzip.open(os.path.join(a.out, "lang.json.gz"), "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump({"names": LANG_NAMES, "byId": lang_out}, f, ensure_ascii=False, separators=(",", ":"))
    with gzip.open(os.path.join(a.out, "native.json.gz"), "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(native, f, ensure_ascii=False, separators=(",", ":"))

    sl = os.path.getsize(os.path.join(a.out, "lang.json.gz"))
    sn = os.path.getsize(os.path.join(a.out, "native.json.gz"))
    print(f"\nwrote lang.json.gz   {sl/1024**2:.2f} MB")
    print(f"wrote native.json.gz {sn/1024**2:.2f} MB")
    print(f"took {time.time()-t0:.0f}s")

    # a quick sanity report: how many titles per language
    from collections import Counter
    c = Counter(lang_out.values())
    print("\ntop languages:")
    for code, cnt in c.most_common(12):
        print(f"   {LANG_NAMES.get(code, code):12s} {cnt:>8,}")

if __name__ == "__main__":
    main()
