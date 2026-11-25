# Qt 6 base (qtbase) for the desktop stack.
#
# freedesktop-sdk 26.08 ships no Qt 6, so the desktop stack builds the
# modules quickshell needs from the official Qt submodule tarballs.
# quickshell links Qt private headers (QtQml/private), which qtbase installs
# by default alongside the public ones.
#
# Configure flags: keep close to Qt's autodetection; bundled copies are used
# only where freedesktop-sdk has no component (pcre2, double-conversion).
# icu exists in fdsdk but is disabled to keep the build surface small; Qt
# works without it.
kind: manual

sources:
- kind: tar
  url: https://download.qt.io/official_releases/qt/6.10/6.10.3/submodules/qtbase-everywhere-src-6.10.3.tar.xz
  ref: 383dc907816338f0cba72088a524c07458dfc69ce684ca9132fcc4fe91c24b0b
  # TODO: bst track — advance with each Qt 6.10.x patch release

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-cmake.bst
# ./configure is a shell wrapper that runs sed; buildsystem-cmake lacks it.
- freedesktop-sdk.bst:components/sed.bst
- freedesktop-sdk.bst:components/perl.bst
- freedesktop-sdk.bst:components/python3.bst
- freedesktop-sdk.bst:components/pkg-config.bst
# system libraries Qt links against
- freedesktop-sdk.bst:components/glib.bst
- freedesktop-sdk.bst:components/dbus.bst
- freedesktop-sdk.bst:components/freetype.bst
- freedesktop-sdk.bst:components/fontconfig.bst
- freedesktop-sdk.bst:components/harfbuzz.bst
- freedesktop-sdk.bst:components/libpng.bst
- freedesktop-sdk.bst:components/jpeg.bst
- freedesktop-sdk.bst:components/zlib.bst
- freedesktop-sdk.bst:components/openssl.bst
- freedesktop-sdk.bst:components/libglvnd.bst
- freedesktop-sdk.bst:components/mesa-headers.bst
- freedesktop-sdk.bst:components/libdrm.bst
- freedesktop-sdk.bst:components/wayland.bst
- freedesktop-sdk.bst:components/libxkbcommon.bst
- freedesktop-sdk.bst:components/libinput.bst
# xcb platform plugin (X11 under xwayland-satellite)
- freedesktop-sdk.bst:components/xorg-lib-xcb.bst
- freedesktop-sdk.bst:components/xcb-util.bst
- freedesktop-sdk.bst:components/xcb-util-cursor.bst
- freedesktop-sdk.bst:components/xcb-util-image.bst
- freedesktop-sdk.bst:components/xcb-util-keysyms.bst
- freedesktop-sdk.bst:components/xcb-util-renderutil.bst
- freedesktop-sdk.bst:components/xcb-util-wm.bst
- freedesktop-sdk.bst:components/xorg-lib-xkbfile.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/glib.bst
- freedesktop-sdk.bst:components/dbus.bst
- freedesktop-sdk.bst:components/freetype.bst
- freedesktop-sdk.bst:components/fontconfig.bst
- freedesktop-sdk.bst:components/harfbuzz.bst
- freedesktop-sdk.bst:components/libpng.bst
- freedesktop-sdk.bst:components/jpeg.bst
- freedesktop-sdk.bst:components/openssl.bst
- freedesktop-sdk.bst:components/libglvnd.bst
- freedesktop-sdk.bst:components/libdrm.bst
- freedesktop-sdk.bst:components/wayland.bst
- freedesktop-sdk.bst:components/libxkbcommon.bst

variables:
  strip-binaries: ""

config:
  build-commands:
  - |
    ./configure -prefix "%{prefix}" -libdir "%{libdir}" \
      -release -opensource -confirm-license \
      -nomake examples -nomake tests -no-pch \
      -system-freetype -fontconfig -system-harfbuzz \
      -system-libpng -system-libjpeg -system-zlib \
      -qt-pcre -qt-doubleconversion -no-icu \
      -openssl-linked \
      -feature-glib -feature-dbus \
      -cmake-generator Ninja
  - cmake --build . --parallel
  install-commands:
  - DESTDIR="%{install-root}" cmake --install .
  - install -Dm644 LICENSES/GPL-3.0-only.txt "%{install-root}%{datadir}/licenses/qt6-base/GPL-3.0-only.txt"
  - "%{install-extra}"
