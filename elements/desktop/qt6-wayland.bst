# Qt Wayland client platform plugin.
# quickshell only needs qtwayland's private headers on Qt < 6.10, but the
# platform plugin itself is required for Qt apps on wayland sessions.
kind: cmake

sources:
- kind: tar
  url: https://download.qt.io/official_releases/qt/6.10/6.10.3/submodules/qtwayland-everywhere-src-6.10.3.tar.xz
  ref: 2e93322a86b562113cfa3a5f0aa8b1e4e185d6284af49b529578d27d52ca85d3
  # TODO: bst track — keep in lockstep with qt6-base

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-cmake.bst
- freedesktop-sdk.bst:components/pkg-config.bst
- freedesktop-sdk.bst:components/wayland.bst
- freedesktop-sdk.bst:components/wayland-protocols.bst
- freedesktop-sdk.bst:components/libxkbcommon.bst
- desktop/qt6-base.bst
- desktop/qt6-declarative.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/wayland.bst
- freedesktop-sdk.bst:components/libxkbcommon.bst
- desktop/qt6-base.bst
