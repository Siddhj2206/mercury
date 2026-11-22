---
name: mercury-review
description: Review Mercury pull requests and work with issues, data-donation reports, labels, and contributor workflow.
---

# Mercury Review and Issue Workflow

Review pull requests and issues with high discipline: minimal diff, correct target branch, evidence-based verification, and strict boundaries.

## When to Use

- Performing code or architecture reviews on PRs in `Siddhj2206/mercury`
- Triaging issues, user-donated diagnostic reports (`mercury report`), or verification comments (`mercury confirm` / `mercury verify`)
- Enforcing contributor guidelines, PR checklists, and commit hygiene

## When NOT to Use

- Writing code changes or authoring elements → load `mercury-buildstream` or `mercury-packaging`
- Modifying signing or publication gates → load `mercury-release`
- Authoring CI workflows → load `mercury-ci`

## Core Process

1. **Verify Target Branch**: All PRs target `main` — Mercury's only branch.
2. **Review Hygiene & Commits**:
   - Check commit format: `<type>(<scope>): <description>`.
   - Ensure commits use `Assisted-by:`, **never** `Co-authored-by:`.
3. **Inspect Implementation**:
   - Ensure image changes use BuildStream elements (no DNF, RPMs, or Containerfiles).
   - Ensure layer additions use `kind: compose` (never `kind: stack`).
   - Check that third-party GitHub Actions are pinned to full commit SHAs.
4. **Evaluate Evidence**:
   - For bugs, check for the diagnostic bundle attached by `mercury report`; `report: attached` on an issue means full structured evidence is present — do not ask the reporter to re-describe it.
   - `mercury confirm` adds another hardware instance; `mercury verify` is post-fix evidence on real hardware.
   - Verify that claimed test results were actually executed (`just validate`, `just boot-test`, etc.).
5. **Constructive Feedback**:
   - If asked to post feedback, compose at most one concise, actionable comment.
   - Never restate GitHub UI status (e.g. "checks are passing").

## Invariants

- **PROHIBITION ON `ublue-os/*`**: Never write to any `ublue-os/*` repository under any circumstance. Ask a human to report upstream manually.
- **Commit Trailer Invariant**: Use `Assisted-by:`, never `Co-authored-by:`.
- **Target Branch**: PRs must target `main`. There are no `testing`/`next` branches.
- **Hardware Evidence Priority**: `mercury verify` attestations on issues are post-ship proof that CI cannot substitute. Do not close bugs without hardware verification or explicit maintainer direction.
- **Triage Labels**: Use `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix` per `docs/agents/triage-labels.md`.
- **Communication Etiquette**: Do not post automated comments or review messages unless explicitly commanded by the user.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I should post a comment acknowledging the PR is open." | Unrequested agent comments create noise. Post only when explicitly instructed. |
| "`Co-authored-by:` is standard GitHub syntax." | Mercury repository policy strictly mandates `Assisted-by:`. |
| "CI passed, the bug is fixed." | Automated boot tests run in QEMU; user hardware has real variance. `mercury verify` closes the loop. |

## Red Flags

- Pull requests with `Co-authored-by:` trailers in commit messages
- Suggesting fixes or workarounds inside `ublue-os/*` repositories
- Closing an issue with `report: attached` without reading the report
- Restating check statuses or queue positions in review comments

## Verification

- [ ] Target branch is confirmed as `main`
- [ ] Commit messages follow conventional standards and use `Assisted-by:`
- [ ] No RPM, DNF, or Containerfile overlays introduced
- [ ] Layer elements use `kind: compose`
- [ ] `just validate` has been confirmed locally or in CI

## References

- [`docs/workflow.md`](../../../docs/workflow.md)
- [`docs/pr-checklist.md`](../../../docs/pr-checklist.md)
- [`docs/feedback-loop.md`](../../../docs/feedback-loop.md)
- [`docs/agents/issue-tracker.md`](../../../docs/agents/issue-tracker.md)
- [`docs/agents/triage-labels.md`](../../../docs/agents/triage-labels.md)
- [`AGENTS.md`](../../../AGENTS.md)
