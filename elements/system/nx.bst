# nx: the user's package manager (github.com/Siddhj2206/nx, Rust workspace
# with an nxd root daemon behind polkit).
#
# Installed from the upstream release tarball, not built from source:
# crates/nx-librpm and nx-solv link the *system* librpm and libsolv
# (docs/adr 0007/0008), which neither freedesktop-sdk nor gnome-build-meta
# provide headers for inside the BST sandbox, and the published release is
# already hash-verified per Fedora release + arch. The tarball is a sealed
# tree (bin, nxd, units+presets, sysusers, tmpfiles, polkit, shell hooks,
# completions, man pages) unpacked at /.
#
# TODO: the tarball is an fc45 build. Confirm the mercury base ships a
# compatible librpm/libsolv ABI (or publish an fcNN matching build) before
# shipping; `nx add` also assumes a Fedora RPM host tier, which needs a
# decision on a non-Fedora base.
# TODO: to build from source instead, source git_repo
# github:Siddhj2206/nx.git and run
# `python3 files/scripts/generate_cargo_sources.py Cargo.lock`; local
# checkout for reference: ../nx.
kind: manual

sources:
- kind: tar
  (?):
  - arch == "x86_64":
      url: github_files:Siddhj2206/nx/releases/download/v1.0.1/nx-v1.0.1-fc45-x86_64.tar.gz
      ref: c49ac4d99c9292fc491e0d217d0778efda447e3d87d09c7161e91e28fa959597
  - arch == "aarch64":
      url: github_files:Siddhj2206/nx/releases/download/v1.0.1/nx-v1.0.1-fc45-aarch64.tar.gz
      ref: f7bfbde5d89394b1644b8569fad6078f3e9cc694c0e0d26c3657e8888de107da

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  strip-binaries: ""

config:
  install-commands:
  # The tarball is a rootfs tree (usr/, etc/); copy contents, not the tree root.
  - cp -rT . "%{install-root}"
  # Enable what neptuno enabled in build/packages/base.toml. The tarball's
  # 90-nx.preset only applies on first boot; wants-symlinks also cover
  # existing installs on upgrade.
  - |
    sysdir="%{install-root}%{indep-libdir}/systemd/system"
    install -d "${sysdir}/sockets.target.wants" "${sysdir}/timers.target.wants" \
               "${sysdir}/multi-user.target.wants"
    ln -sf ../nxd.socket "${sysdir}/sockets.target.wants/nxd.socket"
    for timer in nx-refresh nx-upgrade; do
      ln -sf "../${timer}.timer" "${sysdir}/timers.target.wants/${timer}.timer"
    done
    for svc in nx-select nx-settle nx-sync; do
      ln -sf "../${svc}.service" "${sysdir}/multi-user.target.wants/${svc}.service"
    done
  - |
    userdir="%{install-root}%{indep-libdir}/systemd/user"
    install -d "${userdir}/default.target.wants"
    ln -sf ../nx-notify.path "${userdir}/default.target.wants/nx-notify.path"
    ln -sf ../nx-notify.service "${userdir}/default.target.wants/nx-notify.service"
  - "%{install-extra}"
