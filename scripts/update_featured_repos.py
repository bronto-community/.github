#!/usr/bin/env python3
"""
Read a JSON list of repos from stdin, rank them, and update the featured
projects table in profile/README.md between the FEATURED-REPOS marker comments.

Expected input (piped from `gh api ... | jq -s 'add // []'`):
  [{"name": "...", "description": "...", "url": "...",
    "stars": N, "forks": N, "pushed_at": "ISO-8601"}, ...]
"""
import datetime
import json
import re
import sys

MAX_REPOS = 10
README = "profile/README.md"
MARKER_RE = re.compile(
    r"<!-- FEATURED-REPOS-START -->.*?<!-- FEATURED-REPOS-END -->",
    re.DOTALL,
)


def score(repo: dict, now: datetime.datetime) -> int:
    pushed = datetime.datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
    days_since_push = (now - pushed).days
    recency = max(0, 365 - days_since_push)
    # Stars are the strongest signal; forks and recency break ties.
    return repo["stars"] * 10 + repo["forks"] * 3 + recency


def build_table(repos: list[dict]) -> str:
    rows = ["| Project | What it does |", "|---|---|"]
    for r in repos:
        desc = (r["description"] or "_No description_").replace("|", "\\|")
        rows.append(f"| [{r['name']}]({r['url']}) | {desc} |")
    return "\n".join(rows)


def main() -> None:
    repos = json.load(sys.stdin)
    if not repos:
        print("No repos returned — skipping update.")
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    repos.sort(key=lambda r: score(r, now), reverse=True)
    top = repos[:MAX_REPOS]

    replacement = (
        "<!-- FEATURED-REPOS-START -->\n\n"
        + build_table(top)
        + "\n\n<!-- FEATURED-REPOS-END -->"
    )

    with open(README) as f:
        original = f.read()

    updated = MARKER_RE.sub(replacement, original)

    if updated == original:
        print("Featured repos table is already up to date.")
        return

    with open(README, "w") as f:
        f.write(updated)

    print(f"Updated {README} with {len(top)} featured repo(s).")


if __name__ == "__main__":
    main()
