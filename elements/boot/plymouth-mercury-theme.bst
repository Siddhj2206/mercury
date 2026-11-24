kind: manual

sources:
  - kind: local
    path: files/plymouth

runtime-depends:
  - gnome-build-meta.bst:core-deps/plymouth.bst

build-depends:
  - build-tools/sandbox-tools.bst
  - freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  strip-binaries: ""

config:
  install-commands:
    - install -Dm644 plymouthd.defaults "%{install-root}%{datadir}/plymouth/plymouthd.defaults"
    # spinner theme displays watermark.png as the boot logo.
    - install -Dm644 mercury-boot-logo.png "%{install-root}%{datadir}/plymouth/themes/spinner/watermark.png"
    - install -Dm644 mercury-boot-logo.png "%{install-root}%{datadir}/pixmaps/mercury-boot-logo.png"
    - "%{install-extra}"

public:
  bst:
    overlap-whitelist:
      - "%{datadir}/plymouth/plymouthd.defaults"
      - "%{datadir}/plymouth/themes/spinner/watermark.png"
