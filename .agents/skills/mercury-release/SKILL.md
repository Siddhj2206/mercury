---
name: mercury-release
description: Image publication, cosign verification, dated tags, Secure Boot signing, and rollback-by-rebase for Mercury's single :latest stream.
metadata:
  context7-sources:
    - /sigstore/cosign
    - /bootc-dev/bootc
---

# Mercury Release

Mercury has a deliberately thin release surface: one stream, no promotion, no
rollback workflow. Release work still crosses a cryptographic and security
boundary — stop for human approval before changing signing identities, keys,
token permissions, or provenance.

## When to Use

- Modifying the publish/signing portion of `.github/workflows/build.yml`
- Auditing cosign keyless OIDC signatures, SBOM referrers, or SLSA attestations (`just verify`, `mercury verify`)
- Managing Secure Boot signing: the `secure_boot_signing` option, `MERCURY_SECURE_BOOT_KEY`, `just secure-boot-keygen`, shim/signed-EFI elements
- Tagging, pinning, or rolling back to dated image tags

## When NOT to Use

- Routine CI build or validation workflow updates → load `mercury-ci`
- Local container image builds or testing → load `mercury-image`
- PR review workflows → load `mercury-review`

## Core Process

1. **Trace the Publish Path**: `build.yml` on `main` pushes `:<sha>` (immutable), tags `:latest` (rolling) and `:$VERSION.$DATE` (`YYYY.MM.DD`), signs keyless with cosign, and verifies the signature in-workflow.
2. **Verify Cryptographic Policy**: The cosign certificate identity must match `Siddhj2206/mercury`'s `build.yml` on `refs/heads/main` (see the `verify` recipe in `files/system/shared/usr/share/mercury/justfile` — it matches case-insensitively because GitHub preserves owner capitalisation in the certificate).
3. **Secure Boot Signing**: Signing happens only on `main` with `MERCURY_SECURE_BOOT_KEY` written to a file and removed in an `if: always()` step. The boot layer (`oci/layers/boot.bst`) carries the signed shim chain and verifies signatures in-build (`include/boot-layer.yml`). The base never depends on `secure_boot_signing` — its cache key must be identical either way.
4. **Rollback**: There is no rollback workflow. Roll back by `bootc switch`/`bootc rollback` to a dated `:VERSION.DATE` tag on the device, or revert the merge on `main`.
5. **Human Gate**: Stop and obtain human confirmation before changing signing keys, certificate-identity policy, or push permissions.

## Invariants

- **Anchored Identity**: `--certificate-identity-regexp` is anchored with `^...$` (and `(?i)` where capitalisation differs) and restricted to `build.yml` on `main`.
- **Immutable Anchors**: Refer to images by digest (`@sha256:...`) or `:<sha>` tag when auditing; `:latest` is mutable.
- **Key Hygiene**: `MERCURY_SECURE_BOOT_KEY` never reaches PR jobs; the private key file exists only during the signing pass.
- **Dated Tags Are the Rollback Interface**: `YYYY.MM.DD` tags exist precisely for pinning and rollback — do not add a separate promotion or stream mechanism.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Mercury needs a stable promotion workflow like dakota's." | Single stream by design. `:latest` is the stream; dated tags are the rollback surface. Do not reintroduce promotion machinery. |
| "A regex without `^` and `$` is good enough for cosign identity." | Unanchored regular expressions allow malicious forks or subpaths to forge signatures. Always anchor. |
| "I'll add a rollback workflow for convenience." | Rollback is a device-side `bootc` operation or a git revert. No workflow needed. |

## Red Flags

- Unanchored `--certificate-identity-regexp` in cosign verification commands
- Signing or pushing from any branch other than `main`
- New workflows reintroducing `testing`/`next`/`stable` promotion or variant matrices
- The Secure Boot key file surviving past the signing step

## Verification

- [ ] Certificate identity regex is anchored with `^` and `$` and matches `build.yml@refs/heads/main`
- [ ] `just verify` (or `mercury verify` on a booted system) passes against a published tag
- [ ] Signing inputs and key material never appear in PR job contexts
- [ ] Base element cache keys are identical with and without `secure_boot_signing`
- [ ] Human approval obtained before any signing or key change

## References

- [`.github/workflows/build.yml`](../../../.github/workflows/build.yml)
- [`docs/ci.md`](../../../docs/ci.md)
- [`docs/oci-assembly.md`](../../../docs/oci-assembly.md)
- [`Justfile`](../../../Justfile) (`verify`, `secure-boot-keygen` recipes)
- [`SECURITY.md`](../../../SECURITY.md)
