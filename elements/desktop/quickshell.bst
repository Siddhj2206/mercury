# quickshell — Qt6/QML toolkit that DMS's shell UI runs on.
# Sources: canonical repo is git.outfoxxed.me; the GitHub mirror is used for
# the github: alias.
#
# Disabled features vs upstream defaults: the crash handler (needs cpptrace),
# jemalloc (no fdsdk component; upstream recommends it — see docs note), X11
# (niri uses xwayland-satellite and DMS is wayland-only).
kind: cmake

sources:
- kind: git_repo
  url: github:quickshell-mirror/quickshell.git
  track: 'v[0-9]*.[0-9]*.[0-9]*'
  ref: v0.3.2-0-g4f508be500dea6e5732cc3d50382a0048b17e7b1
  # TODO: bst track — MUST be rebuilt whenever Qt changes (private Qt APIs)

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-cmake.bst
- freedesktop-sdk.bst:components/pkg-config.bst
- freedesktop-sdk.bst:components/spirv-tools.bst
- freedesktop-sdk.bst:components/vulkan-headers.bst
- freedesktop-sdk.bst:components/wayland.bst
- freedesktop-sdk.bst:components/wayland-protocols.bst
- freedesktop-sdk.bst:components/libdrm.bst
# gbm.pc and libgbm.so for the wayland buffer code; mesa provides the
# real backends at runtime (as for niri).
- freedesktop-sdk.bst:components/dummy-gbm.bst
- freedesktop-sdk.bst:components/mesa-headers.bst
- freedesktop-sdk.bst:components/pipewire.bst
- freedesktop-sdk.bst:components/linux-pam.bst
- freedesktop-sdk.bst:components/polkit.bst
- freedesktop-sdk.bst:components/glib.bst
- desktop/cli11.bst
- desktop/qt6-base.bst
- desktop/qt6-declarative.bst
- desktop/qt6-shadertools.bst
- desktop/qt6-svg.bst
- desktop/qt6-wayland.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/wayland.bst
- freedesktop-sdk.bst:components/libdrm.bst
# gbm.pc and libgbm.so for the wayland buffer code; mesa provides the
# real backends at runtime (as for niri).
- freedesktop-sdk.bst:components/dummy-gbm.bst
- freedesktop-sdk.bst:components/pipewire.bst
- freedesktop-sdk.bst:components/linux-pam.bst
- freedesktop-sdk.bst:components/polkit.bst
- freedesktop-sdk.bst:components/glib.bst
- desktop/qt6-base.bst
- desktop/qt6-declarative.bst
- desktop/qt6-svg.bst
- desktop/qt6-wayland.bst

variables:
  cmake-local: >-
    -DDISTRIBUTOR=mercury
    -DCRASH_HANDLER=OFF
    -DUSE_JEMALLOC=OFF
    -DX11=OFF
    -DINSTALL_QML_PREFIX=%{libdir}/qt6/qml
