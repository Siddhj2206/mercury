# Qt SVG — recommended by quickshell; without it SVG icons/images break.
kind: cmake

sources:
- kind: tar
  url: https://download.qt.io/official_releases/qt/6.10/6.10.3/submodules/qtsvg-everywhere-src-6.10.3.tar.xz
  ref: b3223fe005f6a4c7f21f34e4ee6ce0094737cff9503ba15bbb171ac18794f76d
  # TODO: bst track — keep in lockstep with qt6-base

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-cmake.bst
- freedesktop-sdk.bst:components/pkg-config.bst
- desktop/qt6-base.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- desktop/qt6-base.bst
