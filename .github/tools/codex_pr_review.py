from __future__ import annotations

import os
from typing import Any

import requests
from openai import OpenAI


COMMENT_MARKER = "<!-- codex-auto-review -->"
MAX_DIFF_CHARS = 120_000
MAX_PATCH_CHARS_PER_FILE = 12_000
MAX_FILES_BLOCK_CHARS = 80_000


def env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def gh_request(
    method: str,
    url: str,
    token: str,
    *,
    accept: str = "application/vnd.github+json",
    payload: dict[str, Any] | None = None,
) -> Any:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.request(
        method, url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    if accept.endswith(".diff"):
        return response.text
    return response.json()


def gh_request_paginated(url: str, token: str) -> list[dict[str, Any]]:
    """Fetch all pages of a GitHub list endpoint."""
    results: list[dict[str, Any]] = []
    while url:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        results.extend(response.json())
        url = response.links.get("next", {}).get("url")
    return results


def truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}\n\n[...truncated for size...]"


def build_prompt(pr: dict[str, Any], files: list[dict[str, Any]], diff: str) -> str:
    changed_files_summary = []
    for file in files:
        filename = file.get("filename", "unknown")
        status = file.get("status", "modified")
        additions = file.get("additions", 0)
        deletions = file.get("deletions", 0)
        patch = truncate(file.get("patch", ""), MAX_PATCH_CHARS_PER_FILE)
        changed_files_summary.append(
            f"FILE: {filename}\nSTATUS: {status}\n+{additions} / -{deletions}\nPATCH:\n{patch}\n"
        )

    files_block = truncate(
        "\n".join(changed_files_summary), MAX_FILES_BLOCK_CHARS)
    diff_block = truncate(diff, MAX_DIFF_CHARS)
    title = pr.get("title", "")
    body = pr.get("body") or ""
    base_ref = pr.get("base", {}).get("ref", "main")
    head_ref = pr.get("head", {}).get("ref", "unknown")

    return f"""
You are reviewing a GitHub pull request for correctness, reliability, and maintainability.
Focus on bugs, regressions, missing validation, and missing tests.
Be strict but beginner-friendly in tone.

Repository PR metadata:
- Title: {title}
- Base branch: {base_ref}
- Head branch: {head_ref}
- Description:
{body}

Changed files overview:
{files_block}

Unified diff (possibly truncated):
{diff_block}

Output requirements (Markdown):
1. Start with: "### Codex Review"
2. Then "Verdict: APPROVE" or "Verdict: REQUEST_CHANGES" or "Verdict: COMMENT"
3. Then "Findings" as a numbered list.
   - For each finding include:
     - Severity: P0, P1, P2, or P3
     - File path
     - Why it matters
     - Clear suggested fix
4. Then "Testing" section listing tests to add/run.
5. If no significant issues, say "No blocking issues found." and still include lightweight suggestions.

Keep response concise and actionable.
""".strip()


def make_review(openai_api_key: str, model: str, prompt: str) -> str:
    client = OpenAI(api_key=openai_api_key)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": "You are Codex, an expert code reviewer.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        max_output_tokens=1200,
    )
    text = (response.output_text or "").strip()
    if not text:
        return "### Codex Review\nVerdict: COMMENT\n\nFindings\n1. Severity: P2 | File: N/A | Could not parse model output. Retry this workflow.\n\nTesting\n- Re-run workflow."
    return text


def upsert_issue_comment(repo: str, pr_number: str, token: str, body: str) -> None:
    comments_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    comments = gh_request_paginated(f"{comments_url}?per_page=100", token)

    existing = None
    for comment in comments:
        comment_body = comment.get("body", "")
        author_type = comment.get("user", {}).get("type", "")
        if COMMENT_MARKER in comment_body and author_type == "Bot":
            existing = comment
            break

    if existing:
        edit_url = f"https://api.github.com/repos/{repo}/issues/comments/{existing['id']}"
        gh_request("PATCH", edit_url, token, payload={"body": body})
    else:
        gh_request("POST", comments_url, token, payload={"body": body})


def main() -> None:
    github_token = env("GITHUB_TOKEN")
    openai_api_key = env("OPENAI_API_KEY")
    repo = env("REPO")
    pr_number = env("PR_NUMBER")
    pr_action = os.getenv("PR_ACTION", "unknown")
    model = os.getenv("OPENAI_MODEL", "").strip() or "gpt-5.3"

    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    files_url = f"{pr_url}/files?per_page=100"

    pr = gh_request("GET", pr_url, github_token)
    files = gh_request_paginated(files_url, github_token)
    diff = gh_request("GET", pr_url, github_token,
                      accept="application/vnd.github.v3.diff")

    prompt = build_prompt(pr, files, diff)
    review = make_review(openai_api_key, model, prompt)

    sha = pr.get("head", {}).get("sha", "")[:7]
    footer = f"\n\n_Automated by Codex on `{pr_action}` for commit `{sha}` using model `{model}`._"
    comment_body = f"{COMMENT_MARKER}\n{review}{footer}"
    upsert_issue_comment(repo, pr_number, github_token, comment_body)


if __name__ == "__main__":
    main()
