# GitHub Actions for Mercury: limits and best practices

Research notes on what a public repository actually gets from GitHub-hosted
Actions/Packages, and community practices for heavy source builds. Companion
to `docs/ci-research.md` (remote-execution research).

## 1. What public repositories get for free

### Minutes, storage, egress

GitHub Actions on standard GitHub-hosted runners is **free and unlimited on
public repositories** — no minute quota, no egress charge. Source:
[GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
("Use of the standard GitHub-hosted runners is free and unlimited on public
repositories") and
[Billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage)
("GitHub Actions usage is free for standard GitHub-hosted runners in public
repositories, and for self-hosted runners").

GitHub announced in December 2025 that it is *lowering* hosted-runner prices
for paid usage and postponed a planned self-hosted billing change — nothing in
that announcement touches the free-unlimited public-repo policy.
[Changelog](https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/).

### Runner specifications (public repos)

From the public-repo table in the
[runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners):

| Label(s) | CPU | RAM | SSD (free) | Arch |
| --- | --- | --- | --- | --- |
| `ubuntu-latest`, `ubuntu-24.04`, `ubuntu-22.04`, `ubuntu-26.04` | 4 | 16 GB | ~14 GB | x64 |
| `ubuntu-*-arm` | 4 | 16 GB | ~14 GB | arm64 |
| `ubuntu-slim` | 1 | 5 GB | 14 GB | x64 (container, 15-min job cap) |

The "public repos get 4-core Linux runners" rumor is **true and documented**:
public-repo Linux x64 runners are 4 vCPU / 16 GB RAM, versus 2 vCPU / 8 GB
for the same labels on private repos. The disk column is the *free* space —
the underlying disk is larger but filled by the preinstalled toolchain image,
which is why disk-freeing steps matter (see §2).

### Hard limits that apply regardless

From [Actions limits](https://docs.github.com/en/actions/reference/limits):

- **Job execution time: 6 hours** on GitHub-hosted runners (cannot be raised;
  self-hosted allows 5 days). Mercury's `timeout-minutes: 350` build job sits
  just under this ceiling — by necessity, not caution.
- **Workflow run time: 35 days** including waits/approvals.
- **Job concurrency: 20 concurrent jobs** on the Free plan (standard runners).
- **Actions cache storage: 10 GB per repository** — far too small for a
  BuildStream CAS (~100 GB), which is why `validate.yml` correctly rules out
  `actions/cache`.
- **Artifact storage: 500 MB** included on the Free plan; on public repos
  artifact usage is not billed in practice, but artifact *retention* defaults
  to 90 days and is configurable per-upload (`retention-days`, already set to
  7 for build logs).
- Cache service rate limits: 200 uploads / 1500 downloads / 400 deletes per
  minute per repo — irrelevant once the CAS lives in ghcr.

### Larger runners

There is **no free tier of larger runners** for public repos beyond the
4-core standard above. Larger runners (up to 64+ cores, GPU) require a Team
or Enterprise plan and a payment method.
[Reference](https://docs.github.com/en/actions/concepts/runners/larger-runners).
Third-party providers (depot.dev, runs-on, Namespace, Ubicloud, Blacksmith)
sell drop-in `runs-on` replacements with more CPU/disk and per-minute pricing —
the realistic upgrade path if 4 cores/14 GB ever stops being enough, short of
self-hosting.

### GitHub Packages / ghcr

- **Public packages are free**: "GitHub Packages usage is free for public
  packages. In addition, data transferred in from any source is free."
  [Billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages).
- For the Container registry specifically, GitHub has stated container image
  storage and bandwidth is currently free, with a promise of ≥1 month notice
  before any policy change.
  [Working with the Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
- **Delete caveat**: `GITHUB_TOKEN` cannot delete package versions; a classic
  PAT with `delete:packages` (or a GitHub App) is required. `cleanup-bst-cache.yml`
  already encodes this correctly via `CACHE_CLEANUP_TOKEN`.
- Public packages support anonymous pulls; only push/delete need auth.

### Public-repo gotchas

- **Fork PRs get `GITHUB_TOKEN` read-only and no secrets, and `id-token` is
  effectively useless for signing** (fork PRs can't get trusted OIDC identity
  in the base repo's trust policy anyway). `build.yml` already gates builds on
  `head.repo.full_name == github.repository` plus a maintainer `build` label —
  best practice.
- **OIDC identity is exact**: the cosign `--certificate-identity` check in
  `build.yml` pins `build.yml@refs/heads/main` — correct; a regexp would admit
  other workflows/branches.
- **PR `secrets` are not exposed** on `pull_request` from forks — combined with
  the label gate this means untrusted code can't reach `packages: write` or
  `id-token: write`.
- `permissions: read-all` at workflow top with per-job escalation is the
  recommended least-privilege pattern — already used.

## 2. Fast/efficient Actions for heavy source builds

### Disk-space freeing

Hosted Ubuntu images ship tens of GB of toolchains (Android SDK, .NET,
Haskell/GHC, Swift, PowerShell, Docker images, large apt packages). Known
reclaims:

- `jlumbroso/free-disk-space` — the most-used action; removes Android, .NET,
  Haskell, Swift, large packages; ~31 GB in ~3 minutes. Tunable inputs so you
  don't break `setup-*` tool caches.
- Equivalent manual recipes: `sudo rm -rf /usr/share/dotnet
  /usr/local/lib/android /opt/ghc /usr/local/share/powershell /usr/lib/swift`
  plus `docker image prune -af` (pre-seeded moby images eat several GB) and
  `sudo apt-get clean`.

Mercury already does the manual equivalent in both `build.yml` jobs.
**Gap**: it does not prune Docker images (`sudo docker image prune -af` or
`sudo rm -rf /var/lib/docker` before any docker use) — a cheap extra win on a
job that builds an OS image. Consider also clearing swap/`/mnt` tricks used by
distro-image projects (e.g. moving workspace to a fresh ext4 on the freed
space), but the simple removals cover most cases.

### Caching a huge CAS when actions/cache can't

The community pattern for >10 GB caches is exactly what Mercury does: **push
the cache as OCI artifacts to ghcr with oras**. Prior art:

- **tuna-os/tromso** — the project Mercury's `bst-oci-cache` action already
  cites ("tromso-style"); stores BuildStream `cas/`+`artifacts/`+`sources` as
  zstd-tar OCI artifacts and prunes dated tags on a schedule.
- The **Universal Blue** family (Bluefin, Bazzite, ucore) and bootc-image
  builders generally reuse the *image itself* (`--cache-from`/`cache-to` in
  buildah/buildkit) — not applicable to BST, whose CAS is not container
  layers, hence the tar-in-OCI approach.
- Other projects doing tar-in-OCI caches: `earthly` satellite caches,
  nix `cachix`-as-oci experiments, and several yocto/oe CI setups
  (`sstate-cache` pushed via oras).

Practices worth noting from these projects:

- Split the cache into a small always-restore artifact (sources) and a large
  main-only artifact (CAS) — Mercury already does this.
- **Save cache even on failure** so a multi-hour cold build can resume —
  Mercury already does this (`!cancelled()` save).
- Keep a rolling tag per branch plus dated tags, prune dated ones on a
  schedule — Mercury already does this (`cleanup-bst-cache.yml`).
- Compress tars with **zstd** (`tar --zstd` or `zstd -T0`) — already used
  (`sources.tar.zst`, `cas.tar.zst`).

### Concurrency groups

Best practice for a repo with expensive main builds and cheap PR checks:

- PR branches: group by ref, `cancel-in-progress: true` — a new push makes
  the old run worthless. `validate.yml` does this; `build.yml` does it
  conditionally.
- Main: **serialize, never cancel** — a cancelled publish can leave a
  half-pushed image. `build.yml`'s
  `group: mercury-build-${{ github.ref }}` with
  `cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}` is the
  recommended shape (the `|| github.run_id` fallback some guides suggest is
  only needed if you want same-ref events to *not* share a group; here
  serializing same-ref runs is correct).
- Merge queue: `validate.yml` already listens on `merge_group`, which is
  required for the merge queue to have a check to gate on.

### Timeouts, retries, flaky networks

- Always set `timeout-minutes` explicitly (default is 6h — the job cap).
  Mercury sets 350/240/30 — good.
- Retry *the operation*, not the job: large source fetches and image pushes
  fail transiently far more often than builds fail deterministically.
  `build.yml` already retries `podman push` 3×. Gaps worth considering:
  - `oras pull`/`oras push` in `bst-oci-cache` has no retry — wrap in the same
    3-attempt loop used for `podman push`.
  - BST itself retries fetches internally to a degree; `--no-interactive` plus
    `on-error`/`--fetch` pre-fetch steps in the Justfile are the lever.
- For `apt-get` (the qemu/virtiofsd install in `build.yml`) transient mirror
  failures are common — a small `for` retry or `apt-get -o
  Acquire::Retries=3` is standard hardening.
- `fail-fast` semantics: don't wrap the whole build in a retry action
  (`nick-fields/retry`); retrying a 5-hour job from scratch is worse than a
  clean failure with the CAS banked.

### Other notable patterns

- **zstd OCI layers**: `podman push --compression-format=zstd` (already used)
  cuts image push time substantially vs gzip; registries including ghcr accept
  zstd layers.
- **Artifact hygiene**: keep `retention-days` short on per-run logs (7d used);
  public-repo artifacts are unbilled but bloat the storage report and slow the
  "download all artifacts" flow.
- **Merge queue implications**: only cheap checks should be required —
  `merge_group` events can't carry PR labels, so the heavy `build.yml` label
  gate would never fire there anyway. Current split (validate required,
  build label-gated) is queue-compatible.

## Recommendations for Mercury

Already matching best practice — no action needed:

- Label-gated, same-repo-only PR builds; fork PRs can never reach
  signing/push (`build.yml` `if:`).
- `permissions: read-all` + per-job escalation; `id-token: write` scoped to
  the image job.
- Exact cosign certificate-identity verification.
- Main serializes, PRs cancel-in-progress; save-CAS-on-failure;
  sources/CAS split; dated-tag pruning; PAT-based delete.
- zstd push compression; explicit timeouts under the 6h cap; short artifact
  retention; `merge_group` trigger on validate.
- OCI-artifact CAS cache in ghcr — correct answer to the 10 GB
  `actions/cache` limit, matches tromso precedent, free on a public repo.

Gaps worth a small change:

1. **Free more disk in `build.yml`**: add `sudo docker image prune -af` (or
   clear `/var/lib/docker` before podman is needed) and optionally
   `sudo apt-get clean` to the existing free-space step; the preinstalled
   Docker image cache is several GB the BST build could use.
2. **Retry `oras` transfers in `bst-oci-cache`**: a flaky pull currently fails
   the whole restore (or silently misses with `2>/dev/null`); a 3-attempt loop
   matching the `podman push` pattern makes cache restore/save resilient.
3. **Retry `apt-get`** for the qemu/virtiofsd install (`Acquire::Retries=3` or
   a small loop).
4. **Watch the 6h job cap**: `timeout-minutes: 350` leaves ~10 min margin. If
   builds approach that, the fix is cache warmth or remote execution
   (`docs/ci-research.md`), not a bigger timeout.
5. **`ubuntu-slim`** exists now for trivial jobs (1 CPU, 15-min cap): not
   needed today, but scheduled lightweight workflows (scorecard, prune) could
   use it if queue pressure ever matters.
