# Automatic Codex PR Reviews

This repository can run automated Codex reviews on every pull request.

## What It Does
- Triggers on PR open/update events.
- Reads PR metadata and diff.
- Sends review context to OpenAI.
- Posts (or updates) a single bot comment with findings.

## One-Time Setup
1. Go to repo `Settings` -> `Secrets and variables` -> `Actions`.
2. Create repository secret:
   - Name: `OPENAI_API_KEY`
   - Value: your OpenAI API key
3. Optional: create repository variable:
   - Name: `OPENAI_REVIEW_MODEL`
- Value: model name for future overrides (workflow currently pins `gpt-5-mini`)

## Workflow File
- `.github/workflows/codex-pr-review.yml`

## Important Notes
- This is an assistant review, not a replacement for maintainer review.
- `@Temiloluwa-Ogundiran` approval is still required before merge.
- The workflow uses `pull_request_target` and does not run contributor code.

## How Maintainers Use It
1. Contributor opens PR.
2. Wait for `Codex PR Review` workflow comment.
3. Use findings to request fixes.
4. Re-check after contributor pushes updates.

## Quick Verification Checklist
- Open a new PR with a tiny docs-only change.
- Confirm `Run Tests` check passes.
- Confirm `Codex PR Review` check completes.
- Confirm one bot comment exists with marker `<!-- codex-auto-review -->`.
