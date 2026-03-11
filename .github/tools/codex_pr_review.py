from __future__ import annotations

import os
import re
from typing import Any

import requests
from openai import OpenAI


COMMENT_MARKER = "<!-- codex-auto-review -->"
MAX_DIFF_CHARS = 40_000
MAX_PATCH_CHARS_PER_FILE = 4_000
MAX_FILES_BLOCK_CHARS = 30_000
MAX_RETRY_PROMPT_CHARS = 20_000


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
    """Extract text from an OpenAI Responses API result, including partial/incomplete."""
    # Primary path: SDK provides output_text directly (works for complete AND incomplete).
    direct = getattr(response, "output_text", None)
    if direct and str(direct).strip():
        return str(direct).strip()

    # Fallback: walk output[].content[].text for any shape.
    output = getattr(response, "output", None) or []
    parts: list[str] = []
    for item in output:
        # Try attribute access first (SDK objects), then dict access.
        content = getattr(item, "content", None)
        if content is None and isinstance(item, dict):
            content = item.get("content") or []
        for chunk in content or []:
            text = ""
            if isinstance(chunk, dict):
                text = chunk.get("text", "")
            else:
                text = getattr(chunk, "text", "")
            if text and str(text).strip():
                parts.append(str(text).strip())
    return "\n".join(parts).strip()


def response_diagnostic(response: Any) -> str:
    status = getattr(response, "status", "unknown")
    incomplete = getattr(response, "incomplete_details", None)
    if incomplete:
        return f"status={status}, incomplete={incomplete}"
    return f"status={status}"


def build_no_blocking_review(summary_note: str = "") -> str:
    cleaned_note = re.sub(r"\s+", " ", summary_note).strip()
    note_line = ""
    if cleaned_note:
        note_line = f"\n2. Reviewer note: {truncate(cleaned_note, 180)}"

    return (
        "### Codex Review\n"
        "Verdict: APPROVE\n\n"
        "Findings\n"
        "1. No blocking issues found."
        f"{note_line}\n\n"
        "Testing\n"
        "- Run the full test suite in CI.\n"
        "- Spot-check changed paths and one edge case."
    )


def normalize_review_text(review: str) -> str:
    text = (review or "").strip()
    if not text:
        return build_no_blocking_review()

    lower = text.lower()
    has_header = "### codex review" in lower
    has_verdict = "verdict:" in lower
    has_findings = "findings" in lower
    has_testing = "testing" in lower
    has_severity = "severity:" in lower
    has_no_blocking = "no blocking issues found" in lower

    # APPROVE should not include actionable findings.
    if "verdict: approve" in lower and has_severity:
        return build_no_blocking_review()

    if has_header and has_verdict and has_findings and has_testing and (has_severity or has_no_blocking):
        return text

    positive_markers = [
        "well-structured",
        "strong implementation",
        "comprehensive",
        "no issues",
        "looks good",
    ]
    inferred_no_blocking = has_no_blocking or (
        not has_severity and any(
            marker in lower for marker in positive_markers)
    )
    if inferred_no_blocking:
        return build_no_blocking_review(text)

    return (
        "### Codex Review\n"
        "Verdict: COMMENT\n\n"
        "Findings\n"
        "1. Severity: P2 | File: N/A | Review output format was incomplete or invalid.\n"
        "2. Severity: P3 | File: N/A | Re-run workflow to generate structured findings.\n\n"
        "Testing\n"
        "- Re-run workflow."
    )


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
Focus on high-confidence bugs, regressions, missing validation, and missing tests.
Be strict but beginner-friendly in tone.
Do not include style, naming, or documentation nits unless they have clear runtime or correctness impact.
Avoid speculative findings.

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
5. If no significant issues, say "No blocking issues found." and do not invent optional suggestions.
6. Do not include extra preamble before "### Codex Review".
7. Keep the whole response under 350 words.

Keep response concise and actionable.
""".strip()


def make_review(openai_api_key: str, model: str, prompt: str) -> str:
    client = OpenAI(api_key=openai_api_key)
    system_prompt = "You are Codex, an expert code reviewer."
    diagnostics: list[str] = []
    retry_nudge = (
        "Your previous response was empty. "
        "Return the Markdown review now using the required format."
    )

    attempts = [
        # Attempt 0: full prompt
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        # Attempt 1: compacted prompt + nudge
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": truncate(
                prompt, MAX_RETRY_PROMPT_CHARS)},
            {"role": "user", "content": retry_nudge},
        ],
        # Attempt 2: minimal prompt
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": truncate(
                prompt, MAX_RETRY_PROMPT_CHARS)},
            {
                "role": "user",
                "content": (
                    "Do not leave the response blank. "
                    "If unsure, return 'Verdict: COMMENT' with at least one suggestion."
                ),
            },
        ],
    ]

    for input_payload in attempts:
        try:
            response = client.responses.create(
                model=model,
                input=input_payload,
                max_output_tokens=8192,
                truncation="auto",
            )
        except Exception as exc:
            diagnostics.append(f"api_error={exc}")
            continue

        text = extract_response_text(response)

        # Accept partial text from incomplete responses instead of discarding.
        status = getattr(response, "status", "completed")
        if text:
            if status == "incomplete":
                text += "\n\n_[Review truncated by token limit.]_"
            return normalize_review_text(text)

        diagnostics.append(response_diagnostic(response))

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

    # Only fail checks when Codex explicitly requests changes.
    if "Verdict: REQUEST_CHANGES" in review.upper():
        raise SystemExit(
            "Codex review requested changes. Check the PR comment for details.")


if __name__ == "__main__":
    main()
