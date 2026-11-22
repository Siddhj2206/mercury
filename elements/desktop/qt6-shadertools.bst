# Qt Shader Tools — build-time dependency of qt6-declarative.
kind: cmake

sources:
- kind: tar
  url: https://download.qt.io/official_releases/qt/6.10/6.10.3/submodules/qtshadertools-everywhere-src-6.10.3.tar.xz
  ref: c75837e2ea493ec0b9747b227c455d4a12cafe90068abf607992da9a403616c6
  # TODO: bst track — keep in lockstep with qt6-base

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-cmake.bst
- freedesktop-sdk.bst:components/pkg-config.bst
- freedesktop-sdk.bst:components/spirv-tools.bst
- desktop/qt6-base.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- desktop/qt6-base.bst
