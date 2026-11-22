---
name: host-homebrew
description: How Homebrew runs on the Mercury host — prefix spelling rules, the GNU Make requirement, and the failure mode where a failed native gem build bricks the persistent /home/linuxbrew prefix. Use when touching brew.bst, brew-tarball.bst, the brew-toolchain layers, or debugging a broken brew on an installed system.
---

# Host Homebrew

Homebrew on Mercury runs **directly on the host**. The prefix at
`/home/linuxbrew/.linuxbrew` is persistent user data: image updates and reboots
do not repair it, so any bug that corrupts it bricks brew until someone fixes
the prefix by hand.

## When to Use

- Editing `elements/mercury/brew.bst`, `elements/mercury/brew-tarball.bst`, or
  the brew toolchain layers (`elements/oci/layers/brew-toolchain*.bst`)
- A user-facing report that every `brew` command crashes on an installed system
- Reviewing changes that touch the toolchain content of the OCI layers

## When NOT to Use

- General package addition → load `mercury-packaging`

## Invariants (violating either one bricks installed systems)

### 1. The image must ship GNU Make wherever it ships GCC

`bin/brew` **hard-filters PATH to `/usr/bin:/bin:/usr/sbin:/sbin`** before
running anything (see `filter the user environment` in Homebrew's `bin/brew`).
No user PATH, shell profile, or brew-installed make can ever satisfy a native
build — the toolchain **must** be in `/usr/bin`. The
`elements/oci/layers/brew-toolchain*.bst` layers therefore compose
`freedesktop-sdk.bst:components/make.bst` alongside `components/gcc.bst`.

Why it bricks: Homebrew's vendored-gem Bundler install is **not transactional**.
If a native extension build fails (e.g. `make` missing), the gem's Ruby files
stay in `vendor/bundle` without the matching `.so`. Ruby then loads mismatched
gem code against the built-in extension of a different version and **every brew
command crashes at startup** (for example, `brew style` installing `json` Ruby
files while portable Ruby falls back to its built-in JSON native extension).

### 2. Brew must always be invoked as `/home/linuxbrew/.linuxbrew/bin/brew`

Mercury has a real `/home` (no ostree `/var/home` indirection). Homebrew derives
its prefix from the path it was invoked through; the `/var/home` spelling makes
the detected prefix differ from the `/home/linuxbrew` prefix Linux bottles are
built for, so brew **rejects every bottle and falls back to source builds**
(which then hit invariant 1).

Upstream brew ecosystem files used to spell these paths `/var/home/linuxbrew`
because on ostree-based targets `/var/home` is the physical directory and
`/home` is a symlink into it — there, either spelling resolves. Mercury
inverts the layout (real `/home`), which turns the spelling into the
bottle-rejection failure above. `/home/linuxbrew` is the spelling that works
on both layouts; `elements/mercury/sudo-linuxbrew-path.bst` uses it. Fix
upstream `/var/home` regressions via a human, not with a Mercury-side rewrite.

## Repairing a bricked prefix on an installed system

Do **not** delete the prefix (user packages live there) and do not reach for
RPM/DNF — this is a BuildStream image.

1. Get a working `make` without touching the OS: GNU Make's `build.sh`
   bootstraps with only a C compiler (`./configure && ./build.sh`), and the
   host ships GCC.
2. Remove the partial gem installs from
   `Homebrew/Library/Homebrew/vendor/bundle/ruby/<abi>/` — the broken gems'
   `gems/<name>-<ver>`, `specifications/<name>-<ver>.gemspec`,
   `extensions/<arch>/<abi>-static/<name>-<ver>`, and `cache/<name>-<ver>.gem`.
3. Reinstall via Bundler **directly** — `brew install-bundler-gems` cannot work
   (PATH filter, invariant 1). From anywhere:

   ```bash
   HB=/home/linuxbrew/.linuxbrew/Homebrew/Library/Homebrew
   RB=$HB/vendor/portable-ruby/<version>/bin
   env -i HOME="$HOME" USER="$USER" TERM=dumb \
     PATH="$RB:<dir-with-make>:/usr/bin:/bin" \
     GEM_HOME="$HB/vendor/bundle/ruby/<abi>" GEM_PATH="$HB/vendor/bundle/ruby/<abi>" \
     BUNDLE_GEMFILE="$HB/Gemfile" BUNDLE_WITH="style" BUNDLE_FROZEN=true \
     "$RB/bundle" install
   ```

4. Verify: `brew --version`, `brew search <x>`, and `brew style <file>` in a
   tap checkout (the class of command that triggered the incident).

## Failure Modes & Recovery Traps

### Re-arming Trap: Do Not Re-run `brew install-bundler-gems`

Bundler extracts gem files **before** building native extensions. Every failed attempt recreates the exact mismatched-gem crash it was trying to fix. Never retry the high-level brew command to test if it works on an affected machine — fix the PATH and invoke Bundler directly via the repair procedure above.

### Timer Execution Environment

`brew-update.service` and `brew-upgrade.service` (systemd user units) invoke brew with the default systemd PATH. Because `bin/brew` enforces a hard PATH filter, timer-context native builds only ever see `/usr/bin`. This is why GNU Make must live in the base image, never in a user profile or prefix.
