# dgop (dux-gop) — stateless system/process monitor used by DMS widgets.
# Upstream release binary; see docs/desktop-elements.md for why Go binaries
# are shipped prebuilt.
kind: manual

sources:
- kind: remote
  (?):
  - arch == "x86_64":
      url: https://github.com/duxlabs-dev/dux-gop/releases/download/v2.1.1/dgop-linux-amd64.gz
      ref: e71a573bc7df42c0fbb0e8975383226f3772638e17437cca936a9786df57e1d8
  - arch == "aarch64":
      url: https://github.com/duxlabs-dev/dux-gop/releases/download/v2.1.1/dgop-linux-arm64.gz
      ref: 51fba8f18404fab54e89a4ae6933b8cf2cf96db1c1c57812008755523c64adc6
  directory: bin
  # TODO: bst track

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/gzip.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  # Stages a prebuilt binary; the strip tool is not in this sandbox.
  strip-binaries: ""

config:
  install-commands:
  - gunzip -c bin/dgop-linux-*.gz > dgop
  - install -Dm755 dgop "%{install-root}%{bindir}/dgop"
  - "%{install-extra}"
