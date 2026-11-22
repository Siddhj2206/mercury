# DMS (Dux Modular Shell) — quickshell-based desktop shell for niri.
#
# Two source kinds:
#  * git_repo: the dux-shell monorepo; only quickshell/ (QML UI) and assets/
#    are installed, to /usr/share/quickshell/dms.
#  * remote: the upstream prebuilt `dms` Go CLI (dms-distropkg). Building it
#    from source would need ~150 go_module sources vendored by hand — the
#    repo has no go-module generator and upstream's own distro packages use
#    this same prebuilt binary (see distro/fedora/dms.spec). See
#    docs/desktop-elements.md for the tradeoff.
kind: manual

sources:
- kind: git_repo
  url: github:duxlabs-dev/dux-shell.git
  track: 'v[0-9]*.[0-9]*.[0-9]*'
  ref: v2.1.2-0-g43255a46ea01e9d0de1fe8ce9897c0d71566b2a8
  # TODO: bst track — keep in lockstep with the dms-distropkg binary below
  directory: src

- kind: remote
  (?):
  - arch == "x86_64":
      url: https://github.com/duxlabs-dev/dux-shell/releases/download/v2.1.2/dms-distropkg-amd64.gz
      ref: 5d0da60b5aa575fd8407fde83df08c0f4fa29507bbc8c9d5f887053882a30d1c
  - arch == "aarch64":
      url: https://github.com/duxlabs-dev/dux-shell/releases/download/v2.1.2/dms-distropkg-arm64.gz
      ref: 6cf71b33e9bade3fa96b30756598ad4f140d11b9925127a45a12911d15e4611f
  directory: bin

- kind: remote
  url: https://github.com/duxlabs-dev/dux-shell/releases/download/v2.1.2/completion.bash
  ref: 61e116dd2fe4cd87ab203f6a3d193404dd5f3c0c0f6dc262439a64411bcb30c4
  directory: completions
- kind: remote
  url: https://github.com/duxlabs-dev/dux-shell/releases/download/v2.1.2/completion.zsh
  ref: 41fa22da4d8d442583d1914315d82bad47e1e013a81f653d501fbbc4aa16eb2d
  directory: completions
- kind: remote
  url: https://github.com/duxlabs-dev/dux-shell/releases/download/v2.1.2/completion.fish
  ref: 8d5de8fb070817daa9104f92ca0104cfc54ac549068d575a0ced41c4e9c42667
  directory: completions

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/gzip.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
# the shell UI runs on quickshell (dms falls back to `qs` when
# libdux-qt-base.so.0 is absent; both are staged)
- desktop/quickshell.bst
- desktop/dux-qt-base.bst

runtime-depends:
- gnome-build-meta.bst:core-deps/systemd.bst

variables:
  strip-binaries: ""

config:
  install-commands:
  - gunzip -c bin/dms-distropkg-*.gz > dms
  - install -Dm755 dms "%{install-root}%{bindir}/dms"
  # QML shell tree (mirrors distro/fedora/dms.spec %install)
  - |
    install -dm755 "%{install-root}%{datadir}/quickshell/dms"
    cp -a src/quickshell/. "%{install-root}%{datadir}/quickshell/dms/"
  - |
    install -Dm644 src/assets/systemd/dms.service \
      "%{install-root}%{indep-libdir}/systemd/user/dms.service"
  - |
    install -Dm644 src/assets/dms-open.desktop \
      "%{install-root}%{datadir}/applications/dms-open.desktop"
    install -Dm644 src/assets/dev.duxlabs.shell.desktop \
      "%{install-root}%{datadir}/applications/dev.duxlabs.shell.desktop"
    install -Dm644 src/assets/dev.duxlabs.shell.notepad.desktop \
      "%{install-root}%{datadir}/applications/dev.duxlabs.shell.notepad.desktop"
    install -Dm644 src/assets/dev.duxlabs.shell.svg \
      "%{install-root}%{datadir}/icons/hicolor/scalable/apps/dev.duxlabs.shell.svg"
  - install -Dm644 completions/completion.bash "%{install-root}%{datadir}/bash-completion/completions/dms"
  - install -Dm644 completions/completion.zsh "%{install-root}%{datadir}/zsh/site-functions/_dms"
  - install -Dm644 completions/completion.fish "%{install-root}%{datadir}/fish/vendor_completions.d/dms.fish"
  - install -Dm644 src/LICENSE "%{install-root}%{datadir}/licenses/dms/LICENSE"
  - "%{install-extra}"
