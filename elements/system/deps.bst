# Mercury system layer: the source-first replacement for neptuno's
# system_files/ overlay + package-overlay story. Another element wires this
# stack into the image's compose.
kind: stack

depends:
# Shared system overlay: mercury-* units, libexec helpers, kargs, sysctl,
# journald, sudoers, udev, fish defaults, `mercury` just front-end.
- system/overlay-shared.bst

# Desktop session overlay: niri+DMS+ghostty skel,
# portals, mimeapps, theme defaults, session environment.
- system/overlay-desktop.bst

# Display manager for the desktop session (config lives in overlay-desktop).

# User package manager (replaces the Nix story from neptuno).
- system/nx.bst

# Default Flatpak set, consumed by mercury-flatpak-preinstall.timer.
- system/flatpaks.bst
