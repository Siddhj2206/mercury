# Desktop stack aggregate: niri + DMS + greetd + portals + secret service.
# kind: stack produces no filesystem output; the image layer composes from
# this element's dependency graph.
kind: stack

depends:
# Compositor and session
- desktop/niri.bst
- desktop/xwayland-satellite.bst
- desktop/greetd.bst
- desktop/dms-greeter.bst

# Shell
- desktop/dms.bst
- desktop/quickshell.bst
- desktop/dux-qt-base.bst
- desktop/dsearch.bst
- desktop/dgop.bst
- desktop/matugen.bst
- desktop/cava.bst

# Qt6 stack
- desktop/qt6-base.bst
- desktop/qt6-declarative.bst
- desktop/qt6-svg.bst
- desktop/qt6-wayland.bst
- desktop/qt6-multimedia.bst

# Portals (gnome + gtk) — element paths assumed from gnome-build-meta
# core-deps/; see docs/desktop-elements.md
- gnome-build-meta.bst:core-deps/xdg-desktop-portal.bst
- gnome-build-meta.bst:core-deps/xdg-desktop-portal-gnome.bst
- gnome-build-meta.bst:core-deps/xdg-desktop-portal-gtk.bst

# Secret service: oo7 (no gnome-keyring) + gcr's ssh-agent
- gnome-build-meta.bst:core-deps/oo7-daemon.bst
- gnome-build-meta.bst:core-deps/oo7-pam.bst
- gnome-build-meta.bst:core-deps/oo7-portal.bst
- gnome-build-meta.bst:gnomeos-deps/oo7-cli.bst
- gnome-build-meta.bst:sdk/gcr.bst

# GlobalShortcutsProvider for niri global shortcuts
- gnome-build-meta.bst:core/gnome-control-center.bst
