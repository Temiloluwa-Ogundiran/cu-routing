# Maintainer Playbook

This repo is optimized for beginner contributors.

## Maintainer Responsibilities
- Break work into simple issues.
- Assign one contributor per issue.
- Keep PR feedback clear and kind.
- Ensure `@Temiloluwa-Ogundiran` is part of review approvals.

## Assignment Workflow
1. Contributor comments: `Can I take this?`
2. Maintainer assigns contributor in GitHub issue assignee field.
3. Maintainer labels issue:
   - `good-first-issue`
   - `difficulty:easy` or `difficulty:medium`
   - `area:data` / `area:routing` / `area:docs` / `area:testing`
4. Contributor opens PR linked to issue.

## Review Workflow
1. Check PR links exactly one issue.
2. Validate scope matches issue acceptance criteria.
3. Run tests locally (or CI).
4. Request changes with concrete steps if needed.
5. Approve when checklist is complete.
6. Ensure `@Temiloluwa-Ogundiran` approved before merge.

## Codex Review Workflow
1. Maintainer sends PR link or number to Codex in this thread.
2. Codex reviews patch, risks, tests, and regression concerns.
3. Codex returns structured feedback and required changes.
4. Contributor updates PR and requests re-review.
5. Final merge happens only after maintainer approval.

## Automatic Review Bot
- GitHub Action `Codex PR Review` posts automated review feedback on PRs.
- Configure `OPENAI_API_KEY` in repository secrets to enable it.
- Setup guide: `docs/guides/automatic-codex-reviews.md`

## Merge Rules
- Squash and merge preferred for clean history.
- Merge only when all required checks pass.
- `Run Tests` GitHub Action must pass before merge.
- If conflicts exist, ask contributor to rebase/merge latest `main`.
- `main` branch is protected:
  - Pull request required before merge.
  - At least 1 approval required.
  - Code owner review required.
  - Stale approvals dismissed on new commits.
  - Conversation resolution required.
  - Force pushes and deletions blocked.

## Suggested Labels
- `good-first-issue`
- `help wanted`
- `difficulty:easy`
- `difficulty:medium`
- `area:data`
- `area:graph`
- `area:routing`
- `area:docs`
- `area:tests`
