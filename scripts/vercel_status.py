#!/usr/bin/env python3
"""vercel_status.py — what the Vercel token can see, and what happened to the last deployments.

Run this when a push does not show up on the site. It answers three questions in order: is the token
valid, which scope holds the project, and did the newest deployment succeed or fail. A failed build
leaves the previous version live, which looks exactly like "nothing changed".
"""
import datetime, json, os, sys, urllib.error, urllib.request

API = "https://api.vercel.com"


def get(path, token):
    req = urllib.request.Request(API + path, headers={
        "Authorization": f"Bearer {token}", "User-Agent": "filmiset-status"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode("utf-8", "ignore")[:200]}
    except Exception as e:
        return {"error": str(e)[:120]}


def main():
    tok = os.environ.get("VERCEL_TOKEN", "").strip()
    if not tok:
        print("VERCEL_TOKEN is not set"); sys.exit(1)
    print(f"token length: {len(tok)}")

    u = get("/v2/user", tok)
    if u.get("error"):
        print("USER:", u["error"], u.get("body", ""))
    else:
        usr = u.get("user") or {}
        print(f"user: {usr.get('username')} <{usr.get('email')}>")

    t = get("/v2/teams", tok)
    teams = t.get("teams") or []
    if t.get("error"):
        print("TEAMS:", t["error"], "— the token cannot read team scope")
    else:
        print(f"teams: {len(teams)}")
        for x in teams:
            print(f"   {x.get('slug')} | {x.get('name')}")

    p = get("/v9/projects", tok)
    projects = p.get("projects") or []
    if p.get("error"):
        print("PROJECTS:", p["error"])
    else:
        print(f"projects: {len(projects)}")
        for x in projects:
            print(f"   {x.get('name')}  id={x.get('id')}")

    scopes = [None] + [x.get("slug") for x in teams if x.get("slug")]
    for sc in scopes:
        q = "/v6/deployments?limit=6" + (f"&slug={sc}" if sc else "")
        d = get(q, tok)
        ds = d.get("deployments") or []
        print(f"\ndeployments in scope {sc or 'personal'}: {len(ds)}")
        if d.get("error"):
            print("   ", d["error"]); continue
        for x in ds[:6]:
            ts = datetime.datetime.utcfromtimestamp((x.get("created") or 0) / 1000).strftime("%Y-%m-%d %H:%M")
            meta = x.get("meta") or {}
            msg = (meta.get("githubCommitMessage") or "")[:50]
            sha = (meta.get("githubCommitSha") or "")[:7]
            print(f"   {ts}  {str(x.get('state')):10s}  {str(x.get('name')):14s} {sha} {msg}")
            if x.get("errorMessage"):
                print(f"        error: {str(x.get('errorMessage'))[:140]}")


if __name__ == "__main__":
    main()
