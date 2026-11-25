# CLI11 — header-only argument parser, static dependency of quickshell and
# dux-qt-base. Built with CMake (not copied) because both consumers use
# find_package(CLI11 CONFIG), which needs the installed CLI11Config.cmake.
kind: cmake

sources:
- kind: git_repo
  url: github:CLIUtils/CLI11.git
  track: 'v[0-9]*.[0-9]*.[0-9]*'
  ref: v2.7.2-0-gcbd58a3696887b34c70949aef21a71735a0c2ad5
  # TODO: bst track

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-cmake.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  # Header-only: nothing to strip.
  strip-binaries: ""
  cmake-local: >-
    -DCLI11_BUILD_TESTS=OFF
    -DCLI11_BUILD_EXAMPLES=OFF
    -DCLI11_BUILD_DOCS=OFF
    -DCLI11_PRECOMPILED=OFF

config:
  install-commands:
    (>):
    - install -Dm644 LICENSE "%{install-root}%{datadir}/licenses/cli11/LICENSE"
