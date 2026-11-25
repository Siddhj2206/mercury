# dux-qt-base — Dux Labs' quickshell fork built as libdux-qt-base.so.0.
# Required by dms-greeter (it refuses to start without it) and used by the
# dms Go binary to run the shell UI in-process when available, falling back
# to the qs binary from quickshell.bst.
#
# Built from source against desktop/qt6-* (upstream's prebuilt bundle carries
# its own Qt 6.12, which would double the Qt stack).
kind: cmake

sources:
- kind: git_repo
  url: github:duxlabs-dev/dux-qt-base.git
  track: 'v[0-9]*.[0-9]*.[0-9]*'
  ref: v0.4.73-0-g0ea003e30fc92c51943ab7660b58d883708e25c2
  # TODO: bst track — quickshell fork; rebuild whenever Qt changes

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
    -DCMAKE_BUILD_TYPE=RelWithDebInfo
    -DDISTRIBUTOR=mercury
    -DCRASH_HANDLER=OFF
    -DUSE_JEMALLOC=OFF
    -DX11=OFF
