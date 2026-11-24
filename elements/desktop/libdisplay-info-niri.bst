# libdisplay-info 0.3 for niri only. niri's libdisplay-info-sys crate
# accepts only libdisplay-info < 0.4.0, while freedesktop-sdk ships 0.4.0.
# The soname follows the minor version (libdisplay-info.so.3 vs .so.4), so
# both coexist; this copy lives under a private prefix so its headers and
# pkg-config file never overlap the SDK's.
# Exit: drop when niri's Cargo.lock moves to a libdisplay-info crate that
# accepts the SDK's version.
kind: meson

sources:
- kind: git_repo
  url: freedesktop:emersion/libdisplay-info.git
  track: '0.3.*'
  ref: 0.3.0-0-g47a5590e9c4eb35d67651b8c05a55f1a48259329

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-meson.bst
- gnome-build-meta.bst:core-deps/hwdata.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  prefix: /usr/lib/niri/libdisplay-info
  meson-local: >-
    -Ddefault_library=shared

public:
  bst:
    split-rules:
      devel:
        (>):
        - '%{prefix}/include'
        - '%{prefix}/include/**'
        - '%{libdir}/pkgconfig'
        - '%{libdir}/pkgconfig/**'
        - '%{libdir}/libdisplay-info.so'
        - '%{bindir}/di-edid-decode'
