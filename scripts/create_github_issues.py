#!/usr/bin/env python3
"""Create GitHub issues from a YAML specification."""
import argparse
import pathlib
from typing import Any

import requests
import yaml

API_URL = "https://api.github.com"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }


def _load_issues(path: pathlib.Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("YAML must define a list of issues")
    return data


def _get_or_create_milestone(
    repo: str, token: str, title: str, dry_run: bool
) -> int | None:
    url = f"{API_URL}/repos/{repo}/milestones"
    if dry_run:
        print(f"[dry-run] would ensure milestone exists: {title}")
        return None
    resp = requests.get(url, headers=_headers(token))
    resp.raise_for_status()
    for ms in resp.json():
        if ms.get("title") == title:
            return ms.get("number")
    create = requests.post(url, headers=_headers(token), json={"title": title})
    create.raise_for_status()
    return create.json().get("number")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, help="<owner>/<repo> to create issues in")
    ap.add_argument("--token", required=True, help="GitHub token with repo scope")
    ap.add_argument(
        "--file",
        default="scripts/next_phase_issues.yaml",
        help="YAML file describing issues",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = ap.parse_args()

    issues = _load_issues(pathlib.Path(args.file))
    for issue in issues:
        data = {
            "title": issue["title"],
            "body": issue["body"],
            "labels": issue.get("labels", []),
        }
        ms_title = issue.get("milestone")
        if ms_title:
            ms_num = _get_or_create_milestone(args.repo, args.token, ms_title, args.dry_run)
            if ms_num is not None:
                data["milestone"] = ms_num
        if args.dry_run:
            print(f"[dry-run] would create issue: {issue['title']}")
            continue
        resp = requests.post(
            f"{API_URL}/repos/{args.repo}/issues",
            headers=_headers(args.token),
            json=data,
        )
        resp.raise_for_status()
        url = resp.json().get("html_url")
        print(f"Created issue: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
