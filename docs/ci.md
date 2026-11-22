# CI reference

This is a map, not a runbook. Workflow YAML is authoritative when it disagrees
with this page.

## Pipeline

| Workflow | Trigger | Purpose |
|---|---|---|
| `validate.yml` | PRs and pushes to `main`, merge queue | Script checks, patch drift, BST element graph |
| `build.yml` | Relevant pushes to `main`, `build`-labeled same-repo PRs, manual | BST build → export → chunkify → lint → boot test; on main also Secure-Boot sign, push `:sha`, keyless cosign sign+verify, tag `:latest` and `:VERSION.DATE` |
| `track-bst-sources.yml` | Daily schedule, manual | Track source pins; opens bundle PRs and core-junction PRs |
| `vulnerability-scan.yml` | Weekly schedule, manual | Trivy scan of `:latest`, results to code scanning |
| `scorecard.yml` | Weekly schedule, pushes to `main` | OpenSSF Scorecard supply-chain analysis |
| `validate-renovate.yml` | Changes to `renovate.json5` | Config validation |
| `renovate-automerge.yml` | Validate success | Enables auto-merge on `renovate/*` PRs |

## Stream model

One image, one stream. Every successful `main` build publishes:

- `:<commit-sha>` — immutable, always
- `:latest` — rolling stream tag
- `:VERSION.DATE` (`YYYY.MM.DD`) — dated tag for pinning/rollback

There is no `testing`/`next`/`stable` promotion, no stable release workflow,
and no rollback workflow: roll back by rebasing to a dated tag or reverting
the merge.

## Secrets and variables

| Name | Where | Purpose |
|---|---|---|
| `MERCURY_SECURE_BOOT_KEY` (secret) | `build.yml` | PEM private key for Secure Boot chain signing, main only |
| `CAS_URL` (variable), `CASD_CLIENT_CERT` (variable), `CASD_CLIENT_KEY` (secret) | `generate-bst-ci-config` | Optional private BuildBox CAS / remote execution; absent = local build with public read-only caches |

PR jobs never receive `MERCURY_SECURE_BOOT_KEY` and never push; fork PRs are
blocked from the `build` label gate entirely. The Secure Boot key is written
to a file for the signing pass and removed in an `if: always()` step.

## Third-party actions

All non-GitHub actions are pinned to full commit SHAs with a version comment;
the `no-floating-action-tags` pre-commit hook enforces it. Trivy runs as a
container image instead of an action for the same reason (pin its digest to
make it fully immutable).
