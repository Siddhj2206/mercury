# Mercury desktop session overlay (files/system/desktop).
#
# Ported from neptuno/system_files/desktop with neptuno->mercury renames.
# Contents:
#
#   greetd config + PAM live in elements/desktop/greetd.bst (the element
#   ships /etc/greetd/config.toml -> dms-greeter on VT1, a minimal pam.d
#   built for this base, the preset, and default.target -> graphical)
#   /etc/skel/.config              niri, dms, ghostty, topgrade user defaults
#   /etc/xdg/qt6ct and gtk-3.0 settings; niri-portals.conf ships patched in desktop/niri.bst
#   /usr/lib/environment.d         wayland/Qt/IME session environment
#   /usr/lib/systemd/user          dms.service.d drop-in, udiskie.service
#   /usr/lib/tmpfiles.d            seeds /var/lib/flatpak/overrides/global
#   /usr/share/applications        default mimeapps.list
#   /usr/share/glib-2.0/schemas    theme gschema override
#   /usr/share/mercury             niri/ghostty base configs, flatpak overrides
#   /usr/share/xdg-terminal-exec   ghostty as the terminal
#
# The dms/dsearch/udiskie units must start with the compositor, not with every
# user session, so they link into niri.service.wants (mirroring neptuno
# build/packages/desktop.toml [[wants]]). greetd.service is enabled by the
# preset in elements/desktop/greetd.bst, which owns the package.
kind: manual

sources:
- kind: local
  path: files/system/desktop
  directory: overlay

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  strip-binaries: ""

config:
  install-commands:
  - cp -rT overlay "%{install-root}"
  - find "%{install-root}" -type f -exec chmod 644 {} +
  - find "%{install-root}" -type d -exec chmod 755 {} +
  # Units that start with the compositor rather than with every user session.
  - |
    userdir="%{install-root}%{indep-libdir}/systemd/user"
    install -d "${userdir}/niri.service.wants"
    for unit in dms.service dsearch.service udiskie.service; do
      ln -sf "../${unit}" "${userdir}/niri.service.wants/${unit}"
    done
  - "%{install-extra}"
