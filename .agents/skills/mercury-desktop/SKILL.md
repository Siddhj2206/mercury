---
name: mercury-desktop
description: Package, update, and configure the niri + DankMaterialShell desktop stack in Mercury — elements/desktop/ (Qt6, quickshell, niri, dms*, greetd) and files/system/desktop/ conventions. Mercury has no GNOME Shell or Shell extensions.
metadata:
  context7-sources:
    - /apache/buildstream
---

# Mercury Desktop Stack

Mercury's session is **niri + DankMaterialShell (DMS) + greetd + GNOME/GTK
portals + oo7 Secret Service + gcr-ssh-agent**, built from source on the
gnome-build-meta/freedesktop-sdk base. There is no GNOME Shell, mutter, gdm,
or GNOME Shell extension machinery — do not port `shell-extensions` patterns
from upstream dakota.

`docs/desktop-elements.md` is the element-by-element reference; this skill is
the operating procedure.

## When to Use

- Adding, updating, or patching an element under `elements/desktop/`
- Bumping Qt 6, niri, DMS components, quickshell, or greetd
- Editing desktop session files under `files/system/desktop/` (greetd config, portals, user units, `/etc/skel` defaults)
- Diagnosing session startup, greeter, or shell component failures

## When NOT to Use

- Native system software, CLI tools, or daemons → load `mercury-packaging`
- OCI layer composition (`elements/oci/`) → load `mercury-image`
- CI workflows → load `mercury-ci`

## Core Process

1. **Read `docs/desktop-elements.md` first** — it records each element's source, pinned ref, and non-obvious constraints.
2. **Respect the Qt lockstep**: `qt6-{base,shadertools,declarative,svg,wayland,multimedia}` must stay on one Qt release. quickshell and `dux-qt-base` use Qt private headers and must be rebuilt for each Qt bump — keep the bump and the rebuild in one change.
3. **DMS components come from the `duxlabs-dev` org** (renamed from AvengeMedia/DankMaterialShell): `dux-shell` (dms), `dux-gop` (dgop), `dux-search` (dsearch), `dux-greeter` (dms-greeter), `dux-qt-base` (quickshell fork as `libdux-qt-base.so.0`). `dux-qml-common` is a git submodule vendored inside dux-shell and dux-greeter — `kind: git_repo` checks submodules out automatically.
4. **Prebuilt Go binaries are deliberate**: `dms`, `dms-greeter`, `dsearch`, `dgop` ship upstream's signed release binaries (same artifacts upstream's own distro packages ship), because source-first needs a go-module source generator and a go ≥ 1.27 toolchain Mercury doesn't have. Don't convert them to `kind: manual` Go builds without writing `generate_go_sources.py` first — see `docs/desktop-elements.md`.
5. **Register for updates**: Add new elements to `scripts/update_sources.py` (`TRACKED`/`RELEASES`/`DERIVED`/`PINNED`) per the `mercury-packaging` procedure.
6. **Validate and build**:
   ```bash
   just validate
   just bst build desktop/<name>.bst
   ```
   Graph validation does not stage sources or run install commands — build the changed element and inspect its installed files.

## Invariants

- **Qt Version Lockstep**: All six `qt6-*` elements share one release; private-header consumers (quickshell, dux-qt-base) rebuild with it.
- **`desktop/deps.bst` aggregation**: `kind: stack` aggregating everything; wire new desktop elements into it, not directly into OCI layers.
- **Session entry is greetd**: `/etc/greetd/config.toml` runs `dms-greeter --command niri`; `default.target` → `graphical.target`. Session unit files live under `files/system/desktop/`, not scattered element ad-hoc files.
- **oo7, not gnome-keyring**: niri's `niri-portals.conf` is patched (`patches/desktop/niri-portals-oo7-secret.patch`) so Secret Service is oo7.
- **No second Qt**: `dux-qt-base` is built against Mercury's Qt; upstream's prebuilt bundle carries its own Qt and was rejected.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll bump qt6-base alone." | Private-header consumers (quickshell, dux-qt-base) break silently at runtime. Bump all six plus consumers together. |
| "Building dms from source is more correct." | It needs ~hundreds of `go_module` sources and go ≥ 1.27; Mercury has neither generator nor toolchain. Upstream's signed release binaries are the sanctioned path today. |
| "Graph check passed, the element is fine." | `bst show` never extracts archives or runs install commands. Build the element and inspect the artifact. |

## Red Flags

- Qt elements on divergent versions
- A `go build`/`go install` or hand-maintained `go_module` lists in desktop elements
- Adding GNOME Shell, gdm, mutter, or `gnome-shell/extensions/` paths
- Session files added under `files/system/shared/` that belong in `files/system/desktop/`

## Verification

- [ ] `just validate` passes cleanly
- [ ] `just bst build desktop/<name>.bst` succeeds
- [ ] New element wired into `desktop/deps.bst`
- [ ] Element registered in `scripts/update_sources.py`
- [ ] Qt bumps include quickshell and dux-qt-base in the same change

## References

- [`docs/desktop-elements.md`](../../../docs/desktop-elements.md)
- [`elements/desktop/`](../../../elements/desktop/)
- [`files/system/desktop/`](../../../files/system/desktop/)
- [`docs/oci-assembly.md`](../../../docs/oci-assembly.md)
