# Contributing Guide

This project is designed for beginners. Small PRs are preferred.

## Before You Start
1. Read [docs/guides/git-beginner-guide.md](docs/guides/git-beginner-guide.md)
2. Pick an issue from [docs/issues/seed-issues.md](docs/issues/seed-issues.md) or GitHub Issues.
3. Comment `/take` on the issue to request assignment.

## Auto Assignment
- Comment `/take` on an open, unassigned issue.
- The workflow assigns the issue to you automatically.
- The workflow adds `in-progress` and removes `ready` / `available` labels when present.
- The workflow posts branch and PR next-step instructions.

## Branch Naming
Use one of:
- `feature/issue-<number>-short-name`
- `fix/issue-<number>-short-name`
- `docs/issue-<number>-short-name`

## Local Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q 
```

## Coding Rules
- Keep changes focused on one issue.
- Add or update tests for code changes.
- Do not commit generated CSV outputs unless requested.
- Keep functions small and readable.

## Pull Request Rules
- Link the issue number in PR description (`Closes #12`).
- Fill PR template checklist.
- Keep PR small (ideally under 300 lines changed).
- Wait for maintainer review before merge.

## Review + Merge Rules
- At least one maintainer review required.
- `@Temiloluwa-Ogundiran` must be part of approvers for merge.
