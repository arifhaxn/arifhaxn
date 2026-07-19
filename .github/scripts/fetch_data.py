#!/usr/bin/env python3
"""
Merge projects.json (user-curated) with live GitHub data.
Run inside the Action with GITHUB_TOKEN. Produces merged.json for the generator.

User controls: name, repo, logo, description, tags, order (array order).
Auto-fetched:  stars, languages (byte split for the donut), pushed_at.
If the API fails for a repo, the card still renders with config data only.
"""
import json, os, sys, urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")

def gh(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}" if TOKEN else "",
        "User-Agent": "projects-panel",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)

def main():
    with open("projects.json") as f:
        projects = json.load(f)
    for p in projects:
        repo = p.get("repo", "")
        try:
            info = gh(f"https://api.github.com/repos/{repo}")
            p["stars"] = info.get("stargazers_count", 0)
            p["pushed_at"] = info.get("pushed_at")
            if not p.get("description"):
                p["description"] = info.get("description") or ""
            p["languages"] = gh(f"https://api.github.com/repos/{repo}/languages")
        except Exception as e:
            print(f"warn: could not fetch {repo}: {e}", file=sys.stderr)
            p.setdefault("stars", 0)
            p.setdefault("languages", {})
            p.setdefault("pushed_at", None)
    with open("merged.json", "w") as f:
        json.dump(projects, f)
    print(f"merged {len(projects)} projects")

if __name__ == "__main__":
    main()
