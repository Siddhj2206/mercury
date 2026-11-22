# dms-greeter — greetd login screen with the DMS aesthetic.
# Single Go binary with the quickshell UI embedded; launches the greeter
# session under niri (greetd config lives in desktop/greetd.bst).
#
# Uses the upstream release binary: building from source needs go_module
# vendoring plus the dux-qml-common submodule; see docs/desktop-elements.md.
# Requires libdux-qt-base.so.0 (desktop/dux-qt-base.bst) at runtime.
kind: manual

sources:
- kind: remote
  (?):
  - arch == "x86_64":
      url: https://github.com/duxlabs-dev/dux-greeter/releases/download/v2.1.2/dms-greeter-linux-amd64.gz
      ref: 61d70aa875e136f5124c67fe8517ac139ec61c88fb0b6b879b6c7f7e9e93dc95
  - arch == "aarch64":
      url: https://github.com/duxlabs-dev/dux-greeter/releases/download/v2.1.2/dms-greeter-linux-arm64.gz
      ref: fc39875dbe9c7ef53da46edef057fb2008aea47e8c7a969eabc005cd5257370e
  directory: bin
  # TODO: bst track — keep in lockstep with desktop/dms.bst

# Upstream sysusers/tmpfiles for the greeter user and its state dirs.
- kind: remote
  url: https://raw.githubusercontent.com/duxlabs-dev/dux-greeter/v2.1.2/assets/systemd/sysusers-dms-greeter.conf
  ref: 6fd5a090e3c34afed64f8497da7a0980f77fa6cb872a7f6f83cf229dcf54da94
  directory: conf
- kind: remote
  url: https://raw.githubusercontent.com/duxlabs-dev/dux-greeter/v2.1.2/assets/systemd/tmpfiles-dms-greeter.conf
  ref: 3dc267a18f22d06f595a80fb77275db56fe88c48b838db364ba3a1d307572a50
  directory: conf

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/gzip.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- desktop/dux-qt-base.bst
# launches the greeter session under niri
- desktop/niri.bst
- desktop/greetd.bst

config:
  install-commands:
  - gunzip -c bin/dms-greeter-linux-*.gz > dms-greeter
  - install -Dm755 dms-greeter "%{install-root}%{bindir}/dms-greeter"
  - install -Dm644 conf/sysusers-dms-greeter.conf "%{install-root}%{prefix}/lib/sysusers.d/dms-greeter.conf"
  - install -Dm644 conf/tmpfiles-dms-greeter.conf "%{install-root}%{prefix}/lib/tmpfiles.d/dms-greeter.conf"
  - "%{install-extra}"
