# CI reference

This is a map, not a runbook. Workflow YAML is authoritative when it disagrees
with this page.

## Pipeline

| Workflow | Trigger | Purpose |
|---|---|---|
| `validate.yml` | PRs and pushes to `main`, merge queue | Script checks, patch drift, BST element graph |
| `build.yml` | Relevant pushes to `main`, `build`-labeled same-repo PRs, manual, self-dispatched continuations | BST build → export → chunkify → lint → boot test; on main also Secure-Boot sign, push `:sha`, keyless cosign sign+verify, tag `:latest` and `:VERSION.DATE` |
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

## BuildStream cache

Mercury runs its own artifact cache without a server. `just cache-proxy`
starts `scripts/bst_ghcr_cache.py` on the runner: a localhost BuildStream
remote (Remote Asset, CAS and ByteStream over gRPC) that stores one
zstd-compressed pack per artifact in the `mercury-bst-cache` ghcr package,
tagged by the SHA-256 of the artifact's Remote Asset URI.

- **Lazy pulls.** Nothing is restored up front. A pack is downloaded only
  when BuildStream asks for that artifact, so a run whose final image is
  already cached transfers one artifact.
- **Incremental pushes.** On `main`, each artifact is uploaded as soon as it
  is built. A run that hits its time budget keeps everything it finished,
  and `build.yml` dispatches up to three continuation runs that resume from
  the cache, so a cold build completes without anyone pressing re-run.
- **Only what Mercury builds.** Before uploading, the proxy asks
  `gbm.gnome.org` and `cache.freedesktop-sdk.io` whether they serve the
  artifact and skips it if they do. It reads blobs straight from casd's
  object store, so a push copies nothing through gRPC.
- **Artifacts only.** Source pushes are refused: a source, including the
  combined element-sources entry, can carry files staged from the checkout,
  and the signing pass stages the Secure Boot private key. The `image` job,
  which stages that key, runs the proxy read-only; pull requests read and
  never write.

The proxy is the first artifact remote in `buildstream-ci.conf`, ahead of
the public caches: a miss there is a localhost round trip, while a miss on
a public cache costs minutes of retries.

`just test-cache-proxy` runs the proxy against an in-process fake registry
inside the bst2 container; `validate.yml` runs it on every PR.

Packs are never pruned yet. Public ghcr storage is free; when a retention
policy is needed it must keep every artifact in the current
`oci/mercury.bst` closure, not just those a recent run touched, because a
run that finds the final image cached never touches its inputs.

## Secrets and variables

| Name | Where | Purpose |
|---|---|---|
| `MERCURY_SECURE_BOOT_KEY` (secret) | `build.yml` | PEM private key for Secure Boot chain signing, main only |
| `CACHE_CLEANUP_TOKEN` (secret) | `build.yml` | Classic PAT with package read/write for the artifact cache; falls back to `GITHUB_TOKEN`, which cannot always read user-namespace packages |

PR jobs never receive `MERCURY_SECURE_BOOT_KEY` and never push; fork PRs are
blocked from the `build` label gate entirely. The Secure Boot key is written
to a file for the signing pass and removed in an `if: always()` step.

## Third-party actions

All non-GitHub actions are pinned to full commit SHAs with a version comment;
the `no-floating-action-tags` pre-commit hook enforces it. Trivy runs as a
container image instead of an action for the same reason (pin its digest to
make it fully immutable).
