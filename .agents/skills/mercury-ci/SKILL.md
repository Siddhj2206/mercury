---
name: mercury-ci
description: Diagnose or change Mercury validation, build, publish, cache, source-tracking, and scanning workflows.
metadata:
  context7-sources:
    - /apache/buildstream
---

# Mercury CI

Workflow YAML in `.github/workflows/` is the current source of truth. Do not rely on historical runbooks when the workflow says something different. `docs/ci.md` maps the pipeline.

## When to Use

- Modifying or debugging GitHub Actions workflows in `.github/workflows/`
- Diagnosing runner startup, syntax, or permission failures
- Changing build, publish, or validation triggers and artifact flows
- Investigating the OCI BST cache (`.github/actions/bst-oci-cache`) or the optional remote CAS (`CAS_URL`/`CASD_*`)

## When NOT to Use

- Cosign verification, Secure Boot signing policy, or tag/digest questions → load `mercury-release`
- BST element syntax or internal build errors → load `mercury-buildstream`
- Reviewing PRs and issue management → load `mercury-review`

## Core Process

1. **Route the Workflow**: Identify the failing workflow:
   - `validate.yml`: PR and push static checks — script checks, patch drift, BST element graph
   - `build.yml`: BST build → export → chunkify → `bootc container lint` → boot test; on `main` additionally Secure-Boot sign, push `:<sha>`, keyless cosign sign+verify, tag `:latest` and `:$VERSION.$DATE`
   - `track-bst-sources.yml`: daily source tracking, opens bundle and core-junction PRs
   - `vulnerability-scan.yml`: weekly Trivy scan of `:latest`
   - `scorecard.yml`, `validate-renovate.yml`, `renovate-automerge.yml`: supply-chain and Renovate plumbing
   - `cleanup-bst-cache.yml`: weekly prune of dated `mercury-bst-*` cache tags (keeps newest 4)
2. **Inspect at Run SHA**: Read the workflow YAML at the exact commit that executed.
3. **Isolate Root Cause**: Distinguish syntax/permission failure (zero jobs run), source fetch failure, OCI cache restore/save failure, or BST compilation error.
4. **Enforce Least Privilege**: PR jobs never receive `MERCURY_SECURE_BOOT_KEY` and never push; fork PRs cannot get the `build` label gate.
5. **Validate Locally**: Run `just check-publish-workflow` and `just validate` before submitting.

## Invariants

- **Third-Party Actions**: Pin all third-party actions to full 40-character commit SHAs with an inline version comment; the `no-floating-action-tags` pre-commit hook enforces it. Trivy runs as a pinned container image for the same reason.
- **Single Stream**: One image, one stream. Every successful `main` build publishes `:<sha>` (immutable), `:latest` (rolling), and `:VERSION.DATE` (`YYYY.MM.DD`, for pinning/rollback). There is no `testing`/`next`/`stable` promotion and no rollback workflow — roll back by rebasing to a dated tag or reverting the merge.
- **OCI BST Cache**: BuildStream state is cached as ghcr OCI artifacts (`mercury-bst-sources`, `mercury-bst-cas`) via `.github/actions/bst-oci-cache`, not `actions/cache`. Source cache restores on every job; `cas/` + `artifacts/` save runs on `main` only. Next step up if it overflows: a private `buildbox-casd` remote via `CAS_URL`/`CASD_*`.
- **Build Label Gate**: Same-repo PRs labeled `build` run the full `build.yml` build + boot test. Fork PRs are blocked from that gate entirely.
- **Truth in Reporting**: Never report CI as green while workflows are pending, queued, or skipped.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "A commit SHA is overkill; a version tag like `@v2` is fine." | Tags are mutable. Security policy requires 40-character commit SHAs for third-party actions, enforced by pre-commit. |
| "CI is basically green, only one job is still running." | All jobs must complete. A green validate plus a pending build is not a green PR. |
| "`actions/cache` is fine for the BST cache." | The 10 GB cap cannot hold a BST CAS; that's why the OCI cache action exists. |

## Red Flags

- Unpinned third-party actions (using `@v1`, `@main` instead of SHA)
- Granting PR jobs `MERCURY_SECURE_BOOT_KEY` or push permissions
- Reintroducing variant matrices or multi-stream promotion plumbing
- Asserting CI passed when checks are still in progress

## Verification

- [ ] `just check-publish-workflow` passes
- [ ] All modified workflow files pass YAML linting and schema validation
- [ ] Third-party actions are pinned to full commit SHAs with version comments
- [ ] PR description specifies local checks run vs CI status

## References

- [`docs/ci.md`](../../../docs/ci.md)
- [`.github/workflows/`](../../../.github/workflows/)
- [`.github/actions/bst-oci-cache/`](../../../.github/actions/bst-oci-cache/)
- [`Justfile`](../../../Justfile)
