from __future__ import annotations

import os
from typing import Any

import requests
from openai import OpenAI


COMMENT_MARKER = "<!-- codex-auto-review -->"
MAX_DIFF_CHARS = 80_000
MAX_PATCH_CHARS_PER_FILE = 8_000
MAX_FILES_BLOCK_CHARS = 50_000
MAX_RETRY_PROMPT_CHARS = 45_000


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


def extract_response_text(response: Any) -> str:
    direct = (getattr(response, "output_text", "") or "").strip()
    if direct:
        return direct

    output = getattr(response, "output", None) or []
    parts: list[str] = []
    for item in output:
        content = getattr(item, "content", None)
        if content is None and isinstance(item, dict):
            content = item.get("content", [])
        for chunk in content or []:
            if isinstance(chunk, dict):
                chunk_type = chunk.get("type")
                chunk_text = chunk.get("text") or ""
            else:
                chunk_type = getattr(chunk, "type", None)
                chunk_text = getattr(chunk, "text", "") or ""
            if chunk_type in {"output_text", "text"} and str(chunk_text).strip():
                parts.append(str(chunk_text).strip())
    return "\n".join(parts).strip()


def response_diagnostic(response: Any) -> str:
    status = getattr(response, "status", "unknown")
    incomplete = getattr(response, "incomplete_details", None)
    if incomplete:
        return f"status={status}, incomplete={incomplete}"
    return f"status={status}"


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
    system_prompt = "You are Codex, an expert code reviewer."
    input_payload = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    diagnostics: list[str] = []

    for attempt in range(3):
        response = client.responses.create(
            model=model,
            input=input_payload,
            max_output_tokens=2200,
        )
        text = extract_response_text(response)
        if text:
            return text
        diagnostics.append(response_diagnostic(response))

        # Retry with a compacted prompt to reduce response dropout on large diffs.
        if attempt == 0:
            compact_prompt = truncate(prompt, MAX_RETRY_PROMPT_CHARS)
            input_payload = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_prompt},
                {
                    "role": "user",
                    "content": (
                        "Your previous response was empty. "
                        "Return the Markdown review now using the required format."
                    ),
                },
            ]
        else:
            input_payload.append(
                {
                    "role": "user",
                    "content": (
                        "Do not leave the response blank. "
                        "If unsure, return 'Verdict: COMMENT' with at least one non-blocking suggestion."
                    ),
                }
            )

    diag_text = "; ".join(diagnostics) if diagnostics else "status=unknown"
    return (
        "### Codex Review\n"
        "Verdict: COMMENT\n\n"
        "Findings\n"
        "1. Severity: P2 | File: N/A | Model returned an empty response body.\n"
        f"2. Severity: P3 | File: N/A | Response diagnostics: {diag_text}\n\n"
        "Testing\n"
        "- Re-run workflow."
    )


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
    model = os.getenv("OPENAI_MODEL", "").strip() or "gpt-5-mini"

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
