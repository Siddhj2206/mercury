<p align="center"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo/mercury-wordmark-on-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/logo/mercury-wordmark-on-light.svg">
  <img src="assets/logo/mercury-wordmark.svg" alt="mercury" width="480">
</picture></p>

# Mercury

A personal bootc OCI desktop: **niri** + **DankMaterialShell**, assembled
entirely from source with [BuildStream 2](https://buildstream.build/) on a
GNOME-OS-style base (gnome-build-meta + freedesktop-sdk).

Mercury is a source-built fork (in the copy sense) of
[projectbluefin/dakota](https://github.com/projectbluefin/dakota) — the
Bluefin flagship re-imagined from source — itself descended from
[neptuno](https://github.com/projectbluefin/neptuno)-era experiments.
Credit for the build machinery, element layout, and patch discipline goes
to the dakota maintainers.

## What it is

- niri scrollable-tiling Wayland compositor with DankMaterialShell on top
- System libraries and toolchain from freedesktop-sdk, desktop stack from
  gnome-build-meta — no RPMs, no Containerfile, no dnf
- Baseline x86-64 builds that reuse GNOME OS and freedesktop-sdk artifacts
- systemd-boot as the bootloader, with optional Secure Boot signing
- Atomic updates via `bootc` — rebase, rollback, and pin from the registry

## Install / update

```bash
# On any bootc system:
bootc switch ghcr.io/siddhj2206/mercury:latest

# Later:
bootc upgrade
```

Images publish as `:latest` plus an immutable `:VERSION.DATE` tag per build;
a `:<commit-sha>` tag is kept for exact reproduction.

## Secure Boot

Secure Boot signing is wired through the BuildStream graph; enrolling the
vendor key is opt-in on the installed system.

## Verify

Images are signed keylessly with cosign. See [SECURITY.md](SECURITY.md) for
the exact `cosign verify` invocation.

## Building

```bash
just build            # BST build of oci/mercury.bst
just export            # export the OCI image into podman
just boot-test        # boot smoke test in an ephemeral VM
```

Requires podman, just, ~100 GB disk. See [AGENTS.md](AGENTS.md) for the full
workflow and [docs/build.md](docs/build.md) for details.

## Scope

Personal single-maintainer project. No aarch64, no NVIDIA variant, no
gaming spin, no stable/next streams — one rolling `:latest`.

## Known gaps

See the [open issues](https://github.com/Siddhj2206/mercury/issues).
