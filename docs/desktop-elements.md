# Desktop stack elements (elements/desktop/)

Target session: **niri + DankMaterialShell (DMS) + greetd + GNOME/GTK
portals + oo7 Secret Service + gcr-ssh-agent**, on the
gnome-build-meta/freedesktop-sdk base. Ported from neptuno's Fedora
bootc niri/DMS setup (`neptuno/build/packages/desktop.toml`,
`neptuno/build/30-desktop.sh`). No GNOME Shell/mutter/gdm.

`desktop/deps.bst` (`kind: stack`) aggregates everything; another agent
composes it into the image layer.

## Upstream naming note

AvengeMedia/DankMaterialShell was renamed to the **duxlabs-dev** org:
`dux-shell` (dms CLI + QML shell), `dux-gop` (dgop), `dux-search`
(dsearch), `dux-greeter` (dms-greeter), `dux-qt-base` (quickshell fork
built as a shared library), `dux-qml-common` (shared QML widgets,
vendored as a git submodule inside dux-shell and dux-greeter —
`git_repo` checks submodules out automatically).

## Elements

### Qt 6 stack (built from source — fdsdk 26.08 ships no Qt 6)

| Element | Source | Pinned ref |
|---|---|---|
| qt6-base | download.qt.io official qtbase-everywhere-src | 6.10.3 |
| qt6-shadertools | qtshadertools-everywhere-src | 6.10.3 |
| qt6-declarative | qtdeclarative-everywhere-src | 6.10.3 |
| qt6-svg | qtsvg-everywhere-src | 6.10.3 |
| qt6-wayland | qtwayland-everywhere-src | 6.10.3 |
| qt6-multimedia | qtmultimedia-everywhere-src | 6.10.3 |

All six must stay on the same Qt release. quickshell and dux-qt-base use
Qt private headers and **must be rebuilt for each Qt bump** (upstream's
own warning) — keep the Qt bump and the qs rebuild in one change.

qt6-base uses bundled pcre2/double-conversion (fdsdk only has pcre2 as a
bootstrap element; glib vendors its own). icu is disabled. qt6-multimedia
is configured for the gstreamer backend (fdsdk has gstreamer, no ffmpeg).

### Wayland session

| Element | Source | Pinned ref | Notes |
|---|---|---|---|
| niri | github:niri-wm/niri | v26.04 | cargo; Cargo.lock → cargo2 source via `files/scripts/generate_cargo_sources.py`. Pins smithay git rev `ff5fa7d` — the two `kind: git` cargo2 entries are hand-maintained. Ships `niri-session`, `niri.service`/`niri-shutdown.target` (systemd user units), `niri-portals.conf` **patched**: `Secret=gnome-keyring` → `oo7` (patches/desktop/niri-portals-oo7-secret.patch). |
| xwayland-satellite | github:Supreeeme/xwayland-satellite | v0.8.3 | cargo; spawned by niri for X11 clients |
| greetd | github:kennylevinsen/greetd | 0.9.0 | cargo; ships `greetd.service` + preset enabling it, `/etc/greetd/config.toml` (`user=greeter`, `command=dms-greeter --command niri`), `/etc/pam.d/greetd` (pam_unix + optional pam_oo7 auth+session), default.target → graphical.target |
| dms-greeter | github:duxlabs-dev/dux-greeter | v2.1.2 | **prebuilt release binary**; UI embedded; launches greeter under niri; installs upstream sysusers (`greeter` user) + tmpfiles (`/var/cache/dms-greeter`, `/var/lib/greeter`) |

### Shell

| Element | Source | Pinned ref | Notes |
|---|---|---|---|
| quickshell | github:quickshell-mirror/quickshell (mirror of git.outfoxxed.me) | v0.3.2 | cmake; `-DCRASH_HANDLER=OFF` (no cpptrace in fdsdk), `-DUSE_JEMALLOC=OFF` (no jemalloc in fdsdk — upstream *recommends* it for memory fragmentation, open question), `-DX11=OFF` |
| dux-qt-base | github:duxlabs-dev/dux-qt-base | v0.4.73 | cmake; quickshell fork as `libdux-qt-base.so.0`. **Required by dms-greeter**; dms prefers it over `qs` when present. Built against our Qt — upstream's prebuilt bundle carries a second Qt (6.12) and was rejected |
| cli11 | github:CLIUtils/CLI11 | v2.7.2 | header-only, quickshell static dep |
| dms | github:duxlabs-dev/dux-shell | v2.1.2 | git source for QML (`quickshell/` → `/usr/share/quickshell/dms`) + assets (`dms.service`, desktop files, icon); the `dms` Go binary is the **upstream prebuilt `dms-distropkg`** — same artifact upstream's own Fedora spec downloads |
| dsearch | github:duxlabs-dev/dux-search | v2.1.1 | prebuilt binary + `assets/dsearch.service` user unit |
| dgop | github:duxlabs-dev/dux-gop | v2.1.1 | prebuilt binary; DMS telemetry widgets |
| matugen | github:InioX/matugen | v4.2.0 | cargo; DMS wallpaper theming |
| cava | github:karlstav/cava release tar | 1.0.0 | autotools; optional DMS extra, pipewire input |

### Why the Go binaries are prebuilt

`dms`, `dms-greeter`, `dsearch`, `dgop` are Go. Building them
source-first needs every dependency vendored as `go_module` sources —
`dms/core` alone has ~35 direct deps including tailscale.com (~hundreds
of modules transitively), and several need go ≥ 1.27 (fdsdk ships 1.25;
`apps/syncthing-go.bst` has 1.26.6). The repo has no go-module generator
script and `modules.txt`/`git-ref` entries can't be hand-derived safely.
Upstream's own distro packages ship these same signed release binaries.
Dakota already accepts this pattern (`mercury/tailscale.bst` ships the
upstream tarball). To move source-first later: write a
`generate_go_sources.py` alongside `generate_cargo_sources.py` and a
private go ≥ 1.27 toolchain element modeled on `apps/syncthing-go.bst`.

## Junction components assumed to exist

Inventory was taken from a staged freedesktop-sdk 26.08 / gnome-build-meta
checkout (frameless project's .bst cache); verify against mercury's actual
junction pins (`bst show`) before merge.

**freedesktop-sdk (high confidence — confirmed in staged tree):**
rust, rust-bindgen, llvm, go, gcc, cmake, ninja, meson, pkg-config,
perl, python3, make/autotools buildsystems; glib, dbus, linux-pam,
polkit, pipewire(-daemon), wayland, wayland-protocols, libdrm,
mesa-headers, libglvnd, libxkbcommon, libinput, libseat, libevdev,
mtdev, libdisplay-info, hwdata, systemd(-libs), xwayland, xorg-lib-xcb
+ xcb-util-*, freetype, fontconfig, harfbuzz, libpng, jpeg, zlib,
openssl, icu, fftw, inih, gstreamer + plugins-base, spirv-tools,
vulkan-headers, sqlite, brotli, expat, libffi.

**gnome-build-meta (medium-high — names from gbm `core-deps`/`core`/`sdk`,
present in the inspected branch; mercury pins gnome-51):**
`core-deps/xdg-desktop-portal.bst`, `-gnome.bst`, `-gtk.bst`;
`core-deps/oo7-daemon.bst`, `oo7-pam.bst`, `oo7-portal.bst`;
`gnomeos-deps/oo7-cli.bst`; `sdk/gcr.bst` (provides gcr-ssh-agent
socket/prompter); `core/gnome-control-center.bst`
(GlobalShortcutsProvider for niri); `sdk/pango.bst` (build+runtime dep
of niri).

**Not in junctions (built here):** Qt 6 (all modules), quickshell,
dux-qt-base, cli11, niri, xwayland-satellite, greetd, all DMS pieces,
matugen, cava. wlroots is not needed (niri uses smithay, not wlroots).

## Session wiring notes (for the image-assembly agent)

- `greetd.service` is enabled by preset; `default.target` →
  `graphical.target` is shipped by desktop/greetd.bst.
- Boot chain: greetd → `dms-greeter --command niri` (as `greeter`
  user) → user session `niri-session` → `niri.service` (user) →
  `dms.service`, `dsearch.service` via `niri.service` wants/graphical-
  session. neptuno also wires `niri.service.wants/dms.service` —
  `dms.service` itself already has `WantedBy=graphical-session.target`,
  so systemd starts it when niri's unit reaches the session; confirm a
  wants link is still desired to match neptuno's ordering.
- User units to enable by default (neptuno): `gcr-ssh-agent.socket`,
  `oo7-daemon.service`. Their enablement lives in the image layer /
  presets, not these elements.
- `gnome-control-center` is only for niri global shortcuts
  (GlobalShortcutsProvider); neptuno hides its .desktop launcher entry
  (`NoDisplay=true`) at image build time.
- oo7 replaces gnome-keyring entirely; the niri-portals.conf patch
  points the Secret portal at `oo7`. Verify oo7-portal's registered
  portal name is `oo7` on the mercury pin.

## Open questions / risks

1. **Qt 6.10.3 configure flags** — the flag set is conservative; first
   `bst build desktop/qt6-base.bst` may surface missing devel deps
   (likely candidates: more xcb pieces, tslib, or `-no-feature-*`
   trims). Big single build (~1h+).
2. **quickshell private-API coupling** — qs 0.3.2 vs Qt 6.10.3:
   upstream requires rebuilds per Qt release; if qs lags Qt, build
   failures or runtime crashes are likely. dux-qt-base v0.4.73 was
   upstream-rebased past qs v0.3.2, so it tracks close.
3. **jemalloc** — disabled; upstream warns of perceived memory leaks
   without it. fdsdk has no jemalloc element; add one later if RSS
   matters.
4. **greetd PAM** — `/etc/pam.d/greetd` is hand-written; verify
   `pam_oo7` unlock semantics against gbm's oo7-pam (neptuno used
   `auth substack password-auth` + `-auth optional pam_oo7.so` on
   Fedora's PAM layout; ours is a minimal standalone file).
5. **dms-greeter + libdux-qt-base.so.0 lookup** — the greeter resolves
   the lib via: embedded copy → binary's dir → loader path. Whether the
   release binary embeds it is unverified; `desktop/dux-qt-base.bst`
   provides the fallback. If lookup fails, symlink the lib next to the
   binary or set `DMS_GREETER_QS_CHILD` (unsupported upstream).
6. **dms Go binary** — `dms-distropkg` is prebuilt; it may itself
   dlopen `libdux-qt-base.so.0` (staged anyway).
7. **Go version floor** — if/when the Go pieces go source-first, they
   need go ≥ 1.27; fdsdk's go (1.25) and syncthing-go (1.26.6) are too
   old — another private toolchain element would be needed.
8. **smithay git pin** — niri v26.04 builds against a smithay git rev,
   not crates.io; the two cargo2 `kind: git` entries must be kept in
   sync with upstream's Cargo.lock on each bump.
9. **qt6-multimedia** — optional; if the gstreamer feature probe fails,
   either drop the element or fix flags; DMS degrades gracefully.
10. **Rust toolchain floor** — niri requires rustc ≥ 1.87; fdsdk's rust
    component version on the mercury pin should be checked.
