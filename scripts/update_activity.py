#!/usr/bin/env python3
"""Update the Recent public activity section in the profile README."""
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USERNAME = "Kannan-Ramasami"
START = "<!--START_SECTION:activity-->"
END = "<!--END_SECTION:activity-->"


def clean(value, limit=100):
    value = re.sub(r"\s+", " ", str(value or "").replace("`", "'")).strip()
    return value[:limit] + ("…" if len(value) > limit else "")


def main():
    url = f"https://api.github.com/users/{USERNAME}/events/public?per_page=100"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "profile-readme-activity-updater",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=25) as response:
            events = json.loads(response.read().decode("utf-8"))
        if not isinstance(events, list):
            raise ValueError("Unexpected GitHub events response")
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        print(f"Could not fetch public GitHub events: {exc}", file=sys.stderr)
        return 1

    lines = []
    for event in events:
        kind = event.get("type")
        repo = (event.get("repo") or {}).get("name", "")
        if not repo or repo.lower() == f"{USERNAME}/{USERNAME}".lower():
            continue
        payload = event.get("payload") or {}
        base = f"https://github.com/{repo}"
        label, detail, link = None, "", base

        if kind == "PushEvent":
            commits = payload.get("commits") or []
            messages = [clean((c.get("message") or "").splitlines()[0], 70)
                        for c in commits if c.get("message")]
            label = "Pushed code"
            detail = "; ".join(messages[:2]) if messages else f"{payload.get('size', 1)} commit(s)"
            branch = (payload.get("ref") or "").removeprefix("refs/heads/")
            if branch:
                link = f"{base}/commits/{branch}"
        elif kind == "PullRequestEvent":
            pr = payload.get("pull_request") or {}
            action = payload.get("action", "updated")
            label = "Merged a pull request" if action == "closed" and pr.get("merged") else f"Pull request {clean(action)}"
            detail = clean(pr.get("title") or "Pull request")
            link = pr.get("html_url") or base
        elif kind == "IssuesEvent":
            issue = payload.get("issue") or {}
            label, detail, link = f"Issue {clean(payload.get('action', 'updated'))}", clean(issue.get("title") or "Issue"), issue.get("html_url") or base
        elif kind == "IssueCommentEvent":
            issue = payload.get("issue") or {}
            comment = payload.get("comment") or {}
            label, detail, link = "Commented on an issue", clean(issue.get("title") or "Issue"), comment.get("html_url") or issue.get("html_url") or base
        elif kind == "CreateEvent":
            ref_type = clean(payload.get("ref_type", "resource"))
            label = "Created"
            detail = f"{ref_type}: {clean(payload.get('ref'))}" if payload.get("ref") else f"Created a {ref_type}"
        elif kind == "WatchEvent":
            label, detail = "Starred", "Added a star to this repository"
        elif kind == "ForkEvent":
            fork = payload.get("forkee") or {}
            label, detail, link = "Forked", "Created a fork", fork.get("html_url") or base
        elif kind == "ReleaseEvent":
            release = payload.get("release") or {}
            label, detail, link = "Published a release", clean(release.get("name") or release.get("tag_name") or "Release"), release.get("html_url") or base

        if label:
            lines.append(f"- **{label}** · [{repo}]({link}) — {detail}")
        if len(lines) >= 8:
            break

    activity = "\n".join(lines) if lines else "_No recent public events were returned by GitHub. Check back after your next public contribution._"

    try:
        with open("README.md", "r", encoding="utf-8") as file:
            readme = file.read()
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
        updated, count = pattern.subn(lambda _: f"{START}\n{activity}\n{END}", readme, count=1)
        if count != 1:
            raise ValueError("Activity markers not found in README.md")
        if updated == readme:
            print("Activity section is already current.")
            return 0
        with open("README.md", "w", encoding="utf-8", newline="\n") as file:
            file.write(updated)
    except (OSError, ValueError) as exc:
        print(f"Could not update README: {exc}", file=sys.stderr)
        return 1

    print("Updated recent public activity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
