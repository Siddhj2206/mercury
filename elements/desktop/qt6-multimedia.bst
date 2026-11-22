# Qt Multimedia — optional DMS dependency (system sound feedback).
# Built against the gstreamer backend that freedesktop-sdk provides; the
# ffmpeg backend is left off.
kind: cmake

sources:
- kind: tar
  url: https://download.qt.io/official_releases/qt/6.10/6.10.3/submodules/qtmultimedia-everywhere-src-6.10.3.tar.xz
  ref: dd228fe54051e8834ca53e558794742c8814f217849f9dfa8f9a9df80441903a
  # TODO: bst track — keep in lockstep with qt6-base

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-cmake.bst
- freedesktop-sdk.bst:components/pkg-config.bst
- freedesktop-sdk.bst:components/gstreamer.bst
- freedesktop-sdk.bst:components/gstreamer-plugins-base.bst
- desktop/qt6-base.bst
- desktop/qt6-declarative.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/gstreamer.bst
- freedesktop-sdk.bst:components/gstreamer-plugins-base.bst
- desktop/qt6-base.bst
- desktop/qt6-declarative.bst

variables:
  cmake-local: >-
    -DQT_FEATURE_ffmpeg=OFF
    -DQT_FEATURE_gstreamer=ON
