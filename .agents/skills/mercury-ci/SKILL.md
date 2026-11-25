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
- Investigating the BuildStream artifact cache (`scripts/bst_ghcr_cache.py`, `just cache-proxy`)

## When NOT to Use

- Cosign verification, Secure Boot signing policy, or tag/digest questions → load `mercury-release`
- BST element syntax or internal build errors → load `mercury-buildstream`
- Reviewing PRs and issue management → load `mercury-review`

## Core Process

1. **Route the Workflow**: Identify the failing workflow:
   - `validate.yml`: PR and push static checks — script checks, patch drift, BST element graph
   - `build.yml`: parallel BST slice jobs (`slice (kernel|desktop|userland)`, main only) → BST image build (`build`) → export → chunkify → `bootc container lint` → boot test; on `main` additionally Secure-Boot sign, push `:<sha>`, keyless cosign sign+verify, tag `:latest` and `:$VERSION.$DATE`
   - `track-bst-sources.yml`: daily source tracking, opens bundle and core-junction PRs
   - `vulnerability-scan.yml`: weekly Trivy scan of `:latest`
   - `scorecard.yml`, `validate-renovate.yml`, `renovate-automerge.yml`: supply-chain and Renovate plumbing
2. **Inspect at Run SHA**: Read the workflow YAML at the exact commit that executed.
3. **Isolate Root Cause**: Distinguish syntax/permission failure (zero jobs run), source fetch failure, cache proxy failure (`logs/cache-proxy.log` in the `buildstream-logs-<slice>` or `buildstream-logs-x86_64` artifact), a time-budget stop (a continuation run follows), or BST compilation error.
4. **Enforce Least Privilege**: PR jobs never receive `MERCURY_SECURE_BOOT_KEY` and never push; fork PRs cannot get the `build` label gate.
5. **Validate Locally**: Run `just check-publish-workflow` and `just validate` before submitting.

## Invariants

- **Third-Party Actions**: Pin all third-party actions to full 40-character commit SHAs with an inline version comment; the `no-floating-action-tags` pre-commit hook enforces it. Trivy runs as a pinned container image for the same reason.
- **Single Stream**: One image, one stream. Every successful `main` build publishes `:<sha>` (immutable), `:latest` (rolling), and `:VERSION.DATE` (`YYYY.MM.DD`, for pinning/rollback). There is no `testing`/`next`/`stable` promotion and no rollback workflow — roll back by rebasing to a dated tag or reverting the merge.
- **Artifact Cache**: `just cache-proxy` runs `scripts/bst_ghcr_cache.py`, a localhost BuildStream remote storing one pack per artifact in the `mercury-bst-cache` ghcr package. It pulls lazily, pushes each artifact as it is built (main only), skips artifacts the public caches serve, and refuses all source pushes. Any job that stages the Secure Boot key runs it read-only. Never cache with tarballs of the whole CAS or `actions/cache`: restores grow without bound and a timed-out run loses its work.
- **Upstream Pin Freshness**: `gbm.gnome.org` keeps only recent `gnome-51` artifacts. A stale `gnome-build-meta.bst` pin misses nearly every GNOME element even though its keys match upstream; when a junction patch stops applying, fix or drop it so the tracker can move the pin.
- **Build Label Gate**: Same-repo PRs labeled `build` run the full `build.yml` build + boot test. Fork PRs are blocked from that gate entirely.
- **Truth in Reporting**: Never report CI as green while workflows are pending, queued, or skipped.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "A commit SHA is overkill; a version tag like `@v2` is fine." | Tags are mutable. Security policy requires 40-character commit SHAs for third-party actions, enforced by pre-commit. |
| "CI is basically green, only one job is still running." | All jobs must complete. A green validate plus a pending build is not a green PR. |
| "`actions/cache` (or a CAS tarball) is fine for the BST cache." | Both restore everything up front and save only at the end; a 10 GB cap or an hour-long restore follows. The proxy fetches per artifact and banks per artifact. |

## Red Flags

- Unpinned third-party actions (using `@v1`, `@main` instead of SHA)
- Granting PR jobs `MERCURY_SECURE_BOOT_KEY` or push permissions
- Reintroducing variant matrices or multi-stream promotion plumbing
- Asserting CI passed when checks are still in progress

## Verification

- [ ] `just check-publish-workflow` passes
- [ ] `just test-cache-proxy` passes when the cache proxy changes
- [ ] All modified workflow files pass YAML linting and schema validation
- [ ] Third-party actions are pinned to full commit SHAs with version comments
- [ ] PR description specifies local checks run vs CI status

## References

- [`docs/ci.md`](../../../docs/ci.md)
- [`.github/workflows/`](../../../.github/workflows/)
- [`scripts/bst_ghcr_cache.py`](../../../scripts/bst_ghcr_cache.py)
- [`Justfile`](../../../Justfile)
