# Build reference

## Requirements

| Tool | Why | Install |
|---|---|---|
| `podman` (rootful + rootless) | BST container + export/boot | Host package manager |
| `just` | All build/test commands | `brew install just` or package manager |
| `qemu` | VM boot | `brew install qemu` / package manager |
| `virtiofsd` | `just boot-fast` only | Host package manager |
| `bcvk` | Ephemeral VM from container | Auto-installed by `just boot-fast` via cargo |
| ~100 GB disk, ~16 GB RAM | BST cache + parallel builds | — |

### CPU baseline

The x86_64 image requires **x86-64-v3** (Intel Haswell Core or newer,
AMD Excavator or newer, including all Ryzen). Check the exact CPU model: many
Pentium, Celeron, and older Atom processors lack the required features even
when newer than Haswell. VMs must expose v3 features to the guest.

`project.conf` owns the default for both direct BuildStream use and `just`;
CI build, export, and validation use that same default. The option is forwarded
only on x86_64 to GNOME Build Meta and freedesktop-sdk. Expect a substantial
rebuild when switching from baseline artifacts to v3.

For a local baseline x86_64 build, use
`BST_FLAGS="-o x86_64_v3 false" just build` and keep that option for
subsequent export/checkout commands. Direct BuildStream accepts
`bst -o x86_64_v3 false ...` as well.

See [BuildStream project options](https://docs.buildstream.build/master/format_project.html#options).

## Repo layout

| Path | Purpose |
|---|---|
| `elements/freedesktop-sdk.bst` | fdsdk junction — pinned to a release tag |
| `elements/gnome-build-meta.bst` | GBM junction — tracks a `gnome-*` branch |
| `elements/mercury/` | Mercury-specific elements |
| `elements/oci/` | OCI image assembly — layers + final image |
| `patches/linux/` | Kernel patches (via fdsdk linux element) |
| `files/` | Static files installed by elements |
| `.agents/skills/` | Agent skills — discovered and loaded on demand |
| `Justfile` | All local dev commands — run `just --list` first |

## Dev loop

```bash
just validate                  # graph check — always run first (~5 min, no build)

just build                     # build+export the image — warm: minutes; first v3 build: many hours

just lint                      # bootc container lint — must pass before PR

just boot-test                 # automated smoke test — exits 0 on success
just boot-fast                 # interactive ephemeral VM via virtiofs (requires virtiofsd)

just show-me-the-future        # full loop: build → export → disk image → QEMU VM
```

First run is slow (cold BST cache). Subsequent runs are fast — BST caches by content hash.

## Useful BST commands

```bash
just validate                                        # check element graph
just bst build mercury/some-element.bst              # build one element
just bst shell --build mercury/some-element.bst      # sandbox shell
just bst show --deps all oci/mercury.bst             # full dependency graph
```

## Updating source pins

Run the same source-update logic as CI from a feature branch with a clean working
tree:

```bash
just update-sources --list                  # preview the scope, no network or writes
just update-sources                         # CI-managed sources, kernels, and core junctions
just update-sources --group bundle          # everything except core junctions
just update-sources --group core-junctions  # GNOME Build Meta + matching SDK, plugins, patches
just update-sources --group kernels         # kernel refs
just update-sources --element mercury/gum.bst

git diff
just validate
```

The updater needs Python 3, `just`, Podman, `gh` (authenticated for GitHub release
lookups), and `curl` (junction/patch sync). BuildStream runs in the usual container.
It edits local files only: no commits, pushes, workflow dispatches, or PRs.
Run only one updater at a time in a checkout, and avoid editing its target files
while it runs.

"All" means the sources managed by the tracker, not every element or dependency
inside upstream junctions. The source list lives in `scripts/update_sources.py`;
CI reads its matrix from there too. Every element with a network source must be
in `TRACKED`, `KERNELS`, `RELEASES`, or `DERIVED` (a pin that must equal another
component's, moved by that component's updater), or in `PINNED` with the decision
that blocks it; the updater tests enforce this. Prefer a source kind BuildStream
tracks by itself, as freedesktop-sdk and gnome-build-meta do: `git_repo` with a
tag glob, or `anitya` for a release tarball listed on release-monitoring.org;
those elements go in `TRACKED`. `RELEASES` is for what a source kind cannot
express: several assets per release, asset names that embed a build number,
packages that must stay on a series, or a version feed outside
release-monitoring.org. Release assets advance their URLs before BuildStream
tracks checksums, and an element with local patches is staged to prove they
still apply before its update is recorded. Core updates derive the
freedesktop-sdk pin from GNOME Build Meta and run `just patch-sync` plus
`just patch-drift-check`; never track the SDK independently.

### Kernels

Kernel elements are local overrides, not pins inherited from the SDK junction.
`--group kernels` updates just these elements; tracking preserves the checkout's
configured series. After tracking, the updater runs
`bst source fetch --deps none` for each kernel on x86_64, which fetches the
complete source set and applies any downstream patch queues before the pin is
accepted. A fetch or patch failure restores the element's starting contents.
Existing patches are never automatically dropped to make a bump pass.

Source fetching is not compilation or hardware validation. Before shipping,
review the kernel source changes and any downstream patches, then build the
kernel elements (these builds are **not** run by the updater):

```bash
just bst build core/linux-fdsdk.bst
```

Boot verification is still needed before release. When the FDSDK junction
advances, also compare its kernel recipe, `patches/linux/`,
`files/linux/config-utils.sh`, and `files/linux/fdsdk-config.sh` with our
vendored copies. Reconcile changes while preserving Mercury's configuration.

### Release assets and failures

An individual failure restores that update's starting files (the entire element
or junction/patch group), continues the remaining updates, and causes
a nonzero exit. Successful updates remain for review. Validation and builds are
separate; successful [source tracking](https://docs.buildstream.build/master/using_commands.html#bst-source-track)
alone does not prove that updated sources build or that downstream patches apply.
`--group tracked` and `--group tarballs` can rerun
those subsets. `--record-dir` is for CI bundle artifacts, not needed locally.

## What NOT to do

| Don't | Why |
|---|---|
| `rpm-ostree`, `pip install`, `apt-get` in elements | BST-only build; all deps from junctions |
| `$(date)`, `$(hostname)`, `$(curl ...)` in `install-commands` | Breaks reproducibility and BST caching |
| Patch junction files directly | Use `patch_queue` source in the junction `.bst` |
| Open a PR without running `just validate` | Wastes everyone's time |
