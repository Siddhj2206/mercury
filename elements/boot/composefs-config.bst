# Marks the image composefs-native, replacing gnome-build-meta's
# oci/integration/bootc-config.bst, which ships the ostree backend's
# prepare-root.conf. bootc picks the composefs backend for an image with
# /usr/lib/composefs/setup-root-conf.toml and no prepare-root.conf
# (bootc-installation(7), "The storage backend"). The tmpfiles drop-in is
# gnome-build-meta's files/oci/10-bootc.conf, unchanged.
# See docs/adr/0001-sealed-uki-boot.md.
kind: manual

sources:
- kind: local
  path: files/composefs

build-depends:
- build-tools/sandbox-tools.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  strip-binaries: ''

config:
  install-commands:
  - install -Dm644 -t "%{install-root}%{indep-libdir}/composefs" setup-root-conf.toml
  - install -Dm644 -t "%{install-root}%{indep-libdir}/tmpfiles.d" 10-bootc.conf
