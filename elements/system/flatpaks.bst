# Mercury Flatpak preinstall declarations.
#
# Choice (port note): mercury keeps dakota's flatpak *.preinstall descriptor
# approach rather than neptuno's single GKeyFile list. The mechanism is the
# same either way — files land in /usr/share/flatpak/preinstall.d/ and the
# first-boot/timer service consumes them — but splitting per-app files is the
# established convention here (elements/mercury/flatpak-apps.bst) and lets
# variants override single apps.
#
# NOTE: the default app set comes from neptuno's flatpaks/default.preinstall
# (one [Flatpak Preinstall <id>] section per app in a single mercury.preinstall;
# the format allows one file per app later if needed).
#
# system/overlay-shared.bst owns the mercury-flatpak-preinstall.{service,timer}
# units; this element only drops the descriptor list.
kind: manual

sources:
- kind: local
  path: files/oci/mercury-flatpak
  directory: mercury-flatpak
- kind: local
  path: files/service-overrides
  directory: service-overrides

build-depends:
- freedesktop-sdk.bst:bootstrap/bash.bst
- freedesktop-sdk.bst:bootstrap/coreutils.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  strip-binaries: ''

config:
  install-commands:
  - |
    for preinstall in mercury-flatpak/preinstall.d/*.preinstall; do
      install -Dm644 "$preinstall" "%{install-root}/usr/share/flatpak/preinstall.d/$(basename "$preinstall")"
    done
  # Skip the preinstall service cleanly on a flatpak too old to have the
  # subcommand; the ExecCondition probe makes systemd skip rather than fail.
  - |
    install -Dm644 service-overrides/mercury-flatpak-preinstall.service.d/condition-check.conf \
            "%{install-root}%{indep-libdir}/systemd/system/mercury-flatpak-preinstall.service.d/condition-check.conf"
