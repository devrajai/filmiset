#!/usr/bin/env python3
"""
pack_data.py - turn a huge title database (CSV or TSV) into small static files that ANY free host can serve.

  python pack_data.py titles.csv out_dir            # real run (Colab or PC)
  python pack_data.py --selftest 300000 out_test    # test with fake data, no database needed

What it writes (all .json.gz, columnar, small):
  manifest.json            counts, dictionaries (languages, types, genres), file lists
  core.json.gz             the best ~20,000 titles: the suggestion engine runs fully in the browser on this
  lang/<code>_<n>.json.gz  every title of a language, best first, 4,000 per file ("load more" = next file)
  s/<hex>.json.gz          search shards by title prefix (adaptive, max ~1,500 entries each)
  search_keys.json.gz      list of the search shards that exist
  pk/<n>.json.gz           detail packs (overview, cast...) for titles that have them

Your database columns (rename in COLS below if yours differ):
  id, title, year, type, language, votes, rating, genres(comma separated), runtime
  optional detail columns (kept only if present): overview, cast, director, country, tags, poster
"""
import csv, gzip, json, math, os, random, sys, unicodedata, zlib
from collections import defaultdict

COLS = dict(id="id", title="title", year="year", type="type", language="language",
            votes="votes", rating="rating", genres="genres", runtime="runtime")
DETAIL_COLS = ["overview", "cast", "director", "country", "tags", "poster"]
CORE_N = 20000          # titles the engine can use directly in the browser
LANG_PAGE = 4000        # titles per language file
PACKS = 512             # number of detail packs
SEARCH_CAP = 1500       # max entries in one search shard
WORD_MIN_VOTES = 200    # titles below this are searchable by FIRST word only (keeps the index small)
DETAIL_MIN_VOTES = 50   # detail pack only for titles with at least this many votes


def norm(s):
    """Same rule as data-loader.js: keep letters, digits and combining marks (needed for Hindi/Tamil matras)."""
    s = (s or "").lower()
    return " ".join("".join(c if unicodedata.category(c)[0] in "LNM" else " " for c in s).split())


def write_gz(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with gzip.open(path, "wb", compresslevel=9) as f:
        f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return os.path.getsize(path)


def to_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def read_rows(path):
    delim = "\t" if path.endswith((".tsv", ".tsv.txt")) else ","
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=delim):
            yield r


def pack(rows, out):
    langs, types, genres = {}, {}, {}
    idx = lambda d, k: d.setdefault(k, len(d))
    recs, details = [], {}
    sum_r = n_r = 0

    for r in rows:
        title = (r.get(COLS["title"]) or "").strip()
        if not title:
            continue
        votes = to_int(r.get(COLS["votes"]))
        try:
            rating = float(r.get(COLS["rating"]) or 0)
        except ValueError:
            rating = 0.0
        if votes > 0 and rating > 0:
            sum_r += rating; n_r += 1
        gmask = 0
        for g in (r.get(COLS["genres"]) or "").split(","):
            g = g.strip().lower()
            if g:
                gmask |= 1 << idx(genres, g)
        rid = (r.get(COLS["id"]) or "").strip()
        rid = rid[2:] if rid.startswith("tt") and rid[2:].isdigit() else rid     # tt0050083 -> 0050083
        rid = str(int(rid)) if rid.isdigit() else rid
        rec = [rid, title, to_int(r.get(COLS["year"])), idx(types, (r.get(COLS["type"]) or "movie").strip().lower()),
               idx(langs, (r.get(COLS["language"]) or "und").strip().lower()), votes, int(round(rating * 10)),
               gmask, to_int(r.get(COLS["runtime"]))]
        recs.append(rec)
        if votes >= DETAIL_MIN_VOTES:
            d = {k: r[k] for k in DETAIL_COLS if r.get(k)}
            if d:
                details[rid] = d

    avg = (sum_r / n_r) if n_r else 6.5
    m = 1000.0

    def score(rec):                                    # fair rating (few votes pull to average) x fame
        v, r = rec[5], rec[6] / 10
        wr = (v / (v + m)) * r + (m / (v + m)) * avg
        return wr * (1 + math.log10(v + 1) / 6)

    recs.sort(key=score, reverse=True)
    sizes = {}

    def cols(rs):
        return {"i": [x[0] for x in rs], "t": [x[1] for x in rs], "y": [x[2] for x in rs], "k": [x[3] for x in rs],
                "l": [x[4] for x in rs], "v": [x[5] for x in rs], "r": [x[6] for x in rs], "g": [x[7] for x in rs],
                "m": [x[8] for x in rs]}

    sizes["core"] = write_gz(os.path.join(out, "core.json.gz"), cols(recs[:CORE_N]))

    # ---- language files (best first)
    inv_lang = {v: k for k, v in langs.items()}
    per_lang = defaultdict(list)
    for rec in recs:
        per_lang[rec[4]].append(rec)
    lang_pages = {}
    sizes["lang"] = 0
    for li, rs in per_lang.items():
        pages = math.ceil(len(rs) / LANG_PAGE)
        lang_pages[inv_lang[li]] = [len(rs), pages]
        for p in range(pages):
            sizes["lang"] += write_gz(os.path.join(out, "lang", "%s_%d.json.gz" % (inv_lang[li], p)),
                                      cols(rs[p * LANG_PAGE:(p + 1) * LANG_PAGE]))

    # ---- search shards (adaptive prefix; every word for popular titles, first word only for the rest)
    entries = []
    for rec in recs:
        words = norm(rec[1]).split()
        if not words:
            continue
        keep = words if rec[5] >= WORD_MIN_VOTES else words[:1]
        for w in dict.fromkeys(keep):
            if len(w) >= 2 or w == words[0]:
                entries.append((w, rec[5], rec))
    shards = {}

    def split(es, key):
        if len(es) <= SEARCH_CAP or len(key) >= 6:
            es.sort(key=lambda e: -e[1]); shards[key] = es[:SEARCH_CAP]; return
        groups = defaultdict(list)
        for e in es:
            groups[e[0][:len(key) + 1] if len(e[0]) > len(key) else key].append(e)
        for k, g in groups.items():
            if k == key:
                g.sort(key=lambda e: -e[1]); shards[key] = g[:SEARCH_CAP]
            else:
                split(g, k)

    first = defaultdict(list)
    for e in entries:
        first[e[0][:2]].append(e)
    for k, g in first.items():
        split(g, k)
    sizes["search"] = 0
    for key, es in shards.items():
        sizes["search"] += write_gz(os.path.join(out, "s", key.encode("utf-8").hex() + ".json.gz"), cols([e[2] for e in es]))
    sizes["keys"] = write_gz(os.path.join(out, "search_keys.json.gz"), sorted(shards))

    # ---- detail packs
    buckets = defaultdict(dict)
    for rid, d in details.items():
        buckets[zlib.crc32(rid.encode()) % PACKS][rid] = d
    sizes["packs"] = sum(write_gz(os.path.join(out, "pk", "%d.json.gz" % n), b) for n, b in buckets.items())

    inv = lambda d: [k for k, _ in sorted(d.items(), key=lambda kv: kv[1])]
    manifest = {"version": 1, "titles": len(recs), "core": min(CORE_N, len(recs)), "langPage": LANG_PAGE, "packs": PACKS,
                "types": inv(types), "languages": inv(langs), "genres": inv(genres), "langPages": lang_pages,
                "searchShards": len(shards), "withDetails": len(details)}
    write_gz(os.path.join(out, "manifest.json.gz"), manifest)
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
    return manifest, sizes


def fake_rows(n, seed=7):
    rnd = random.Random(seed)
    a = ["Dil", "Pyaar", "Zindagi", "Raat", "Mohabbat", "Jungle", "Shadi", "Dost", "Sapna", "Kahani", "Raja", "Rani", "Hero",
         "Love", "Night", "Dream", "King", "Last", "Secret", "Road", "दिल", "प्यार", "ज़िंदगी", "காதல்", "కథ"]
    b = ["Story", "Diaries", "Returns", "Express", "Ki Kahani", "Wala", "Ka Safar", "Part 2", "Beyond", "of Fire", "में", "கதை"]
    langs = ["hi"] * 30 + ["en"] * 30 + ["ta"] * 8 + ["te"] * 8 + ["ml"] * 5 + ["gu"] * 3 + ["ko"] * 5 + ["ja"] * 5 + ["fr"] * 3 + ["es"] * 3
    for i in range(n):
        votes = int(rnd.lognormvariate(4.5, 2.2))
        yield {"id": "tt%07d" % (i + 1), "title": "%s %s %s" % (rnd.choice(a), rnd.choice(b), rnd.choice(a) if rnd.random() < .5 else i % 977),
               "year": rnd.randint(1950, 2026), "type": rnd.choice(["movie"] * 5 + ["series", "short"]),
               "language": rnd.choice(langs), "votes": votes, "rating": round(min(9.9, max(1, rnd.gauss(6.3, 1.2))), 1),
               "genres": ",".join(rnd.sample(["Drama", "Comedy", "Romance", "Thriller", "Action", "Horror", "Family", "Crime"], rnd.randint(1, 3))),
               "runtime": rnd.randint(8, 190),
               "overview": ("A story about love, loss and family number %d. " % i) * 2 if votes > 60 else ""}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--selftest"]:
        n, out = int(a[1]), a[2]
        man, sz = pack(fake_rows(n), out)
    elif len(a) == 2:
        man, sz = pack(read_rows(a[0]), a[1])
    else:
        print(__doc__); sys.exit()
    tot = sum(sz.values())
    print("titles:", man["titles"], "| languages:", len(man["languages"]), "| search shards:", man["searchShards"])
    print("sizes (MB):", {k: round(v / 1e6, 1) for k, v in sz.items()}, "| TOTAL %.1f MB" % (tot / 1e6))
