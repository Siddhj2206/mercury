# CLI11 — header-only argument parser, static dependency of quickshell.
kind: manual

sources:
- kind: git_repo
  url: github:CLIUtils/CLI11.git
  track: 'v[0-9]*.[0-9]*.[0-9]*'
  ref: v2.7.2-0-gcbd58a3696887b34c70949aef21a71735a0c2ad5
  # TODO: bst track

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  # Header-only: nothing to strip.
  strip-binaries: ""

config:
  install-commands:
  - mkdir -p "%{install-root}%{prefix}/include"
  - cp -a include/CLI "%{install-root}%{prefix}/include/"
  - install -Dm644 LICENSE "%{install-root}%{datadir}/licenses/cli11/LICENSE"
  - "%{install-extra}"
