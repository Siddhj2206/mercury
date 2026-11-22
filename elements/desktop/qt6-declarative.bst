# Qt Declarative (QtQml/QtQuick) — required by quickshell.
# Installs the QtQml private headers quickshell needs; private headers under
# include/*/6.10.3/ are part of the standard qtdeclarative install.
kind: cmake

sources:
- kind: tar
  url: https://download.qt.io/official_releases/qt/6.10/6.10.3/submodules/qtdeclarative-everywhere-src-6.10.3.tar.xz
  ref: dadf80d43b8e08ca63aa65d46859a42b920a7777cf7e0ecfcb4c4537f9e65c76
  # TODO: bst track — keep in lockstep with qt6-base

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-cmake.bst
- freedesktop-sdk.bst:components/pkg-config.bst
- freedesktop-sdk.bst:components/python3.bst
- desktop/qt6-base.bst
- desktop/qt6-shadertools.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- desktop/qt6-base.bst
