kind: manual

sources:
  - kind: local
    path: files/plymouth

runtime-depends:
  - gnome-build-meta.bst:core-deps/plymouth.bst

build-depends:
  - core/sandbox-tools.bst
  - freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  strip-binaries: ""

config:
  install-commands:
    # No boot-logo watermark is shipped yet; the spinner theme stays
    # unbranded until files/plymouth gains a mercury-boot-logo.png.
    - install -Dm644 plymouthd.defaults "%{install-root}%{datadir}/plymouth/plymouthd.defaults"
    - "%{install-extra}"

public:
  bst:
    overlap-whitelist:
      - "%{datadir}/plymouth/plymouthd.defaults"
