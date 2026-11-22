# Mercury shared system overlay (files/system/shared).
#
# Ported from neptuno/system_files/shared with neptuno->mercury renames and
# the Nix integration dropped (nx owns the package-manager story). Contents:
#
#   /etc/sudoers.d/mercury-bootc          wheel NOPASSWD for `bootc upgrade`
#   /usr/bin/mercury                      `just` front-end (system.just-style
#                                         recipes in /usr/share/mercury/justfile)
#   /usr/lib/bootc/kargs.d                fresh-install kernel args
#   /usr/lib/dracut/dracut.conf.d         initramfs driver omissions (gbm initramfs is dracut)
#   /usr/lib/environment.d, sysctl.d, journald.conf.d
#   /usr/libexec/mercury/*                ensure-homes, flatpak-preinstall, update-notify
#   /usr/lib/systemd/system*              mercury-* units + drop-ins,
#                                       coreos-sulogin-force-generator
#   /usr/lib/systemd/user                 mercury-update-notify user units
#   /usr/lib/udev/rules.d                 input uaccess rule
#   /usr/share/fish/vendor_conf.d         interactive-shell defaults
#   /usr/share/mercury/justfile
#
# Enablement is done here as wants-symlinks (the dakota convention used by
# bindmounts.bst and swapfile.bst), mirroring the units neptuno enabled in
# build/packages/*.toml. The shipped unit files stay under /usr/lib.
kind: manual

sources:
- kind: local
  path: files/system/shared
  directory: overlay

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  strip-binaries: ""

config:
  install-commands:
  - cp -rT overlay "%{install-root}"
  # Deterministic permissions: regular files 644, executables fixed below,
  # sudoers read-only.
  - find "%{install-root}" -type f -exec chmod 644 {} +
  - find "%{install-root}" -type d -exec chmod 755 {} +
  - chmod 0755 "%{install-root}/usr/bin/mercury"
  - chmod 0755 %{install-root}/usr/libexec/mercury/{ensure-homes,flatpak-preinstall,update-notify}
  - chmod 0755 "%{install-root}/usr/lib/systemd/system-generators/coreos-sulogin-force-generator"
  - chmod 0440 "%{install-root}/etc/sudoers.d/mercury-bootc"
  # System enablement, mirroring neptuno build/packages/base.toml.
  - |
    sysdir="%{install-root}%{indep-libdir}/systemd/system"
    install -d "${sysdir}/multi-user.target.wants" "${sysdir}/timers.target.wants"
    ln -sf ../mercury-ensure-homes.service \
           "${sysdir}/multi-user.target.wants/mercury-ensure-homes.service"
    for timer in mercury-flatpak-preinstall mercury-flatpak-update mercury-appstream-refresh; do
      ln -sf "../${timer}.timer" "${sysdir}/timers.target.wants/${timer}.timer"
    done
  # User enablement, mirroring neptuno's [services].user list.
  - |
    userdir="%{install-root}%{indep-libdir}/systemd/user"
    install -d "${userdir}/default.target.wants" "${userdir}/timers.target.wants"
    ln -sf ../mercury-update-notify.path \
           "${userdir}/default.target.wants/mercury-update-notify.path"
    ln -sf ../mercury-update-notify.timer \
           "${userdir}/timers.target.wants/mercury-update-notify.timer"
  - "%{install-extra}"
