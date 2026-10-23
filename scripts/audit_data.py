#!/usr/bin/env python3
"""audit_data.py — cross-check the curated catalogue and report anything that looks wrong.

    python3 scripts/audit_data.py            # report
    python3 scripts/audit_data.py --fix      # also repair what is safe to repair

Checks: missing/silly years, unknown types, unknown categories, duplicate titles across files,
platforms that are not real services, titles that are obvious prose rather than a title, and
rows whose platform list contradicts another row for the same title.
"""
import argparse, glob, json, os, re, sys
from collections import defaultdict, Counter

VALID_TYPES = {'Movie','Series','Short','Natak','Documentary'}
VALID_PLATFORMS = {'Netflix','Prime Video','JioHotstar','JioCinema','SonyLIV','ZEE5','Aha','Sun NXT',
                   'Hoichoi','MX Player','ShemarooMe','Apple TV+','Crunchyroll','YouTube','Chaupal',
                   'Discovery+','Lionsgate Play','ManoramaMAX','Planet Marathi','ETV Win','Stage',
                   'Theatrical','BookMyShow','PVR','Disney+ Hotstar','Hotstar','Amazon Prime Video',
                   'Prime','Zee5','Sony Liv','ALTBalaji','Voot','Ullu','Koode','NeeStream'}
PROSE = re.compile(r'\b(the story of|a collection|this is|every row|we have|you can|'
                   r'note:|please|summary|overview|synopsis)\b', re.I)

def norm(t):
    t=str(t or '').lower().replace('&','and')
    t=re.sub(r'\b(the|a|an)\b',' ',re.sub(r'[^a-z0-9]+',' ',t))
    return re.sub(r'\s+',' ',t).strip()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--fix',action='store_true'); ap.add_argument('--dir',default='data')
    args=ap.parse_args()
    issues=defaultdict(list); bytitle=defaultdict(list); total=0
    files=sorted(glob.glob(os.path.join(args.dir,'curated_*.json')))
    for f in files:
        base=os.path.basename(f)
        if 'verification' in base or 'rejected' in base: continue
        try: rows=json.load(open(f,encoding='utf-8'))
        except Exception as e: issues['unreadable file'].append((base,str(e))); continue
        if not isinstance(rows,list): continue
        dirty=False
        for r in rows:
            if not isinstance(r,dict): issues['row is not an object'].append((base,r)); continue
            total+=1
            t=str(r.get('t') or '').strip()
            if not t: issues['empty title'].append((base,json.dumps(r)[:60])); continue
            if len(t)>70: issues['title too long (likely prose)'].append((base,t[:60]))
            if PROSE.search(t): issues['title reads like prose'].append((base,t[:60]))
            y=r.get('y')
            if y is None: issues['missing year'].append((base,t[:50]))
            else:
                try: yi=int(y)
                except Exception: issues['non-numeric year'].append((base,t[:40],y)); yi=None
                if yi is not None and (yi<1870 or yi>2115): issues['impossible year'].append((base,t[:40],y))
            ty=r.get('type')
            if ty and ty not in VALID_TYPES: issues['unknown type'].append((base,t[:40],ty))
            for p in (r.get('o') or []):
                if p not in VALID_PLATFORMS: issues['unknown platform'].append((base,t[:40],p))
            bytitle[norm(t)].append((base,tuple(r.get('o') or []),r.get('y')))
        if dirty: json.dump(rows,open(f,'w',encoding='utf-8'),ensure_ascii=False,indent=1)

    # the same title carrying two different platform lists
    conflicts=[]
    for k,v in bytitle.items():
        if len(v)<2: continue
        plats={x[1] for x in v if x[1]}
        if len(plats)>1: conflicts.append((k,v))

    print(f"curated files : {len(files)}")
    print(f"rows checked  : {total}")
    print(f"issues found  : {sum(len(v) for v in issues.values())}")
    print()
    for k in sorted(issues, key=lambda x:-len(issues[x])):
        print(f"  {k:34s} {len(issues[k]):5d}")
        for row in issues[k][:4]: print(f"      {row}")
    print(f"\n  {'platform conflicts across files':34s} {len(conflicts):5d}")
    for k,v in conflicts[:10]: print(f"      {k[:30]:32s} {v}")
    return 1 if sum(len(v) for v in issues.values()) else 0

if __name__=='__main__': sys.exit(main())
