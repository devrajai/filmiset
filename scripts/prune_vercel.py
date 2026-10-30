#!/usr/bin/env python3
"""prune_vercel.py — delete old Vercel deployments so the storage quota stops filling up.

Vercel's free tier counts every deployment against 10 GB. This project hit 100%: each deployment
used to carry the whole data folder, 273 MB, before the data moved to Cloudflare, and thirty of them
were enough. Keeping the newest few and deleting the rest brings it back to almost nothing, and
because deployments are now about 2 MB it will not creep up again.

    VERCEL_TOKEN=xxx python3 prune_vercel.py --keep 3
    VERCEL_TOKEN=xxx python3 prune_vercel.py --keep 3 --dry-run
"""
import argparse, json, os, sys, time, urllib.error, urllib.request

API = "https://api.vercel.com"

def call(path, token, method="GET"):
    req = urllib.request.Request(API + path, method=method,
                                 headers={"Authorization": f"Bearer {token}",
                                          "User-Agent": "filmiset-prune"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8")
        return json.loads(body) if body.strip() else {}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--project", default="", help="only this project")
    a = ap.parse_args()

    tok = os.environ.get("VERCEL_TOKEN", "").strip()
    if not tok:
        print("VERCEL_TOKEN is not set"); sys.exit(1)

    try:
        me = call("/v2/user", tok)
        u = me.get("user") or {}
        print(f"user: {u.get('username') or u.get('email') or '?'}")
    except urllib.error.HTTPError as e:
        print(f"token rejected: HTTP {e.code}")
        print(e.read().decode("utf-8", "ignore")[:300])
        sys.exit(1)

    # Deployments belong to a team, not a user. Querying without a team returns an empty list for
    # anyone whose projects live under one — which is what happened first time: the token was valid,
    # the user resolved, and the API said zero deployments. Find the teams, then ask within each.
    teams = []
    try:
        t = call("/v2/teams", tok)
        teams = [{"id": x.get("id"), "slug": x.get("slug"), "name": x.get("name")}
                 for x in (t.get("teams") or [])]
        print(f"teams: {len(teams)}")
        for x in teams:
            print(f"   {x['slug']:24s} {x['name']}")
    except Exception as e:
        print("teams lookup failed:", str(e)[:80])

    scopes = [None] + [x["slug"] for x in teams] if teams else [None]

    # collect every deployment from every scope, paging until the API stops giving more
    deps, until = [], None
    seen = set()
    for scope in scopes:
        until = None
        for _ in range(20):
            q = "/v6/deployments?limit=100"
            if scope: q += f"&slug={scope}"
            if a.project: q += f"&projectId={a.project}"
            if until: q += f"&until={until}"
            try:
                d = call(q, tok)
            except Exception as e:
                print(f"  scope {scope or 'personal'}: {str(e)[:60]}")
                break
            batch = d.get("deployments") or []
            if not batch: break
            for x in batch:
                if x.get("uid") and x["uid"] not in seen:
                    seen.add(x["uid"]); deps.append(x)
            if len(batch) < 100: break
            until = batch[-1].get("created")
            if not until: break
            time.sleep(0.2)
        print(f"  scope {scope or 'personal'}: running total {len(deps)}")

    deps.sort(key=lambda x: x.get("created", 0), reverse=True)
    print(f"found {len(deps)} deployments")
    for d in deps[:6]:
        msg = ((d.get("meta") or {}).get("githubCommitMessage") or "")[:55]
        print(f"   keep? {d.get('uid','')[:12]}  {d.get('state','?'):10s} {msg}")

    victims = deps[a.keep:]
    print(f"\nkeeping {min(a.keep, len(deps))}, deleting {len(victims)}")
    if a.dry_run:
        for d in victims[:15]:
            print("   would delete", d.get("uid", "")[:12])
        print("dry run — nothing deleted")
        return

    ok = fail = 0
    for d in victims:
        uid = d.get("uid")
        if not uid: continue
        try:
            sc = (d.get("teamId") and next((x["slug"] for x in teams if x["id"] == d["teamId"]), None)) or None
            path = f"/v13/deployments/{uid}" + (f"?slug={sc}" if sc else "")
            call(path, tok, method="DELETE")
            ok += 1
            if ok % 5 == 0: print(f"   deleted {ok}…")
        except urllib.error.HTTPError as e:
            fail += 1
            print(f"   failed {uid[:12]}: HTTP {e.code}")
        except Exception as e:
            fail += 1
            print(f"   failed {uid[:12]}: {str(e)[:60]}")
        time.sleep(0.2)

    print(f"\ndeleted {ok}, failed {fail}")

    try:
        left = call("/v6/deployments?limit=100", tok)
        print("deployments remaining:", len(left.get("deployments") or []))
    except Exception:
        pass

if __name__ == "__main__":
    main()
