# INI parser library cava requires (its configure fails without it).
# freedesktop-sdk ships inih, a different library.
kind: cmake

sources:
- kind: git_repo
  url: github:ndevilla/iniparser.git
  track: 'v[0-9]*.[0-9]*.[0-9]*'
  ref: v4.3.2-0-g4fff3f22b63819d30ad5c2e4d7c7df9ec272cffc

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-cmake.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  cmake-local: >-
    -DBUILD_DOCS=OFF
    -DBUILD_EXAMPLES=OFF
    -DBUILD_TESTING=OFF
    -DBUILD_STATIC_LIBS=OFF
