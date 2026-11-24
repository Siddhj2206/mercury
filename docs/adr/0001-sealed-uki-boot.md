# 0001: Sealed UKI boot on the composefs backend

Status: proposed

## Context

Mercury boots shim → Mercury-signed systemd-boot → Mercury-signed kernel,
with an ostree-backend deployment (gnome-build-meta's `prepare-root.conf`,
composefs enabled) and a separate, unsigned initramfs. The installer seals
the LUKS key to PCR 7, and `mercury-secure-boot reseal` manages the move to
Secure Boot. PCR 7 does not cover the kernel, so unlock already survives
updates, but nothing authenticates the initramfs, the kernel command line or
the root filesystem: anyone with the disk can swap the initramfs and still
get TPM unlock.

bootc 1.17 (Mercury's pin) supports *sealed* images on its composefs backend
([bootc-composefs(7)], [sealed images]): one UKI per deployment holds the
kernel, initramfs and command line, with the root filesystem's composefs
digest in the command line, signed for Secure Boot. Firmware authenticates
the UKI, the UKI authenticates the digest, fs-verity authenticates every
file. systemd-stub measures the UKI into PCR 11, and `ukify
--pcr-private-key` signs the expected PCR 11 values, so
`systemd-cryptenroll --tpm2-public-key` binds unlock to "any UKI Mercury
signed" instead of one set of values ([systemd-cryptenroll(1)], [ukify(1)]).
systemd-boot validates through shim (`src/boot/shim.c`), so the MOK chain
keeps working. gnome-build-meta's `gnomeos/signed-boot.bst` already builds
signed UKIs with signed PCR policies for GNOME OS; it is the template.

## Decision

Move Mercury to sealed UKIs on the composefs backend, in three steps, each
boot-tested before the next:

1. **composefs backend, traditional boot.** Ship
   `/usr/lib/composefs/setup-root-conf.toml`, drop the ostree
   `prepare-root.conf`, and patch gnome-build-meta's initramfs `50-bootc`
   module (via `patch_queue`) to carry `setup-root-conf.toml`; it already
   carries `bootc-root-setup.service`. Root filesystem moves off XFS (see
   below).
2. **Signed UKI.** In the signing pass, `bootc container
   split-kernel-and-rootfs`, then `bootc container ukify` with the Mercury
   Secure Boot key; the UKI goes to `/boot/EFI/Linux/`. PR builds produce an
   unsigned UKI.
3. **Signed PCR policy.** Add a PCR signing key pair, pass
   `--pcr-private-key`/`--pcr-public-key`/`--pcrpkey` to ukify as
   `signed-boot.bst` does, and move `mercury-secure-boot` from PCR 7 value
   binding to `--tpm2-public-key` (PCR 11) plus PCR 7.

## Consequences

- **Reinstall.** bootc has no in-place ostree → composefs transition yet;
  existing installs must reinstall to get any of this.
- **Root filesystem.** Sealed images require fs-verity, which XFS lacks.
  ext4 is CI-tested upstream; btrfs is "expected to work, not tested".
  `files/bootc-install/00-defaults.toml` changes from `xfs`.
- **No automatic rollback.** The composefs backend has no boot counting or
  `bootc-boot-complete.service`; a bad update needs a manual rollback.
- **Fixed command line.** kargs come from `/usr/lib/bootc/kargs.d` at build
  time and are signed into the UKI; per-machine kargs need UKI addons, which
  are experimental.
- **New secret.** The PCR signing private key joins
  `MERCURY_SECURE_BOOT_KEY` as a CI secret.
- **Digest must be final.** The composefs digest is of the exact final
  tree. Anything that changes file content or metadata after `ukify`
  (chunkah rechunking, the fakecap xattr restore) breaks boot. Step 2 must
  prove the digest of the published image equals the one in the UKI.

## Open questions

- ext4 or btrfs for root?
- Does chunkah preserve every attribute the composefs digest covers, or must
  ukify run on chunkah's output?
- Should step 3 keep PCR 7 in the policy alongside PCR 11, as `signed-boot.bst`
  does for the initrd phase?

[bootc-composefs(7)]: https://github.com/bootc-dev/bootc/blob/v1.17.3/docs/src/bootc-composefs.7.md
[sealed images]: https://github.com/bootc-dev/bootc/blob/v1.17.3/docs/src/building/bootc-sealed-images.7.md
[systemd-cryptenroll(1)]: https://www.freedesktop.org/software/systemd/man/latest/systemd-cryptenroll.html
[ukify(1)]: https://www.freedesktop.org/software/systemd/man/latest/ukify.html
