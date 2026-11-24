# Mercury's package manifest: generic tools and services layered over the
# freedesktop-sdk runtime. Desktop-session content lives in desktop/deps.bst
# and core services in system/deps.bst (see oci/layers/mercury-stack.bst).
# Add or remove image content via `.bst` elements here — never via
# dnf/RPM/Containerfile overlay logic. Sections follow the elements/ layout.
kind: stack

depends:
  # ── boot ─────────────────────────────────────────────────────────────
  - boot/kexec-disable.bst
  - boot/bootc-install-config.bst
  # efibootmgr and mokutil stay in every image: the Secure Boot tools in
  # the boot layer (oci/layers/boot-stack.bst) run them but cannot carry them.
  - boot/efibootmgr.bst
  - gnome-build-meta.bst:freedesktop-sdk-extra.bst:components/mokutil.bst

  # ── system ───────────────────────────────────────────────────────────
  - system/zswap-config.bst
  - system/swapfile.bst
  - system/composefs-loop-udisks-ignore.bst
  - system/udev-groups.bst
  - system/bindmounts.bst
  - system/uutils-coreutils.bst
  - system/xdg-terminal-exec.bst
  - system/network.bst
  - system/networkmanager-polkit.bst
  - system/nfs-utils.bst
  - freedesktop-sdk.bst:components/which.bst
  # Things missing from the base image
  - gnome-build-meta.bst:core-deps/fwupd.bst

  # ── auth ─────────────────────────────────────────────────────────────
  - auth/sudo-rs.bst
  - auth/sudo-linuxbrew-path.bst
  - auth/fprintd-system-auth.bst
  - auth/fprintd-fingerprint-auth.bst
  - auth/oo7-passwd-pam.bst
  - auth/pam-u2f.bst

  # ── hardware ─────────────────────────────────────────────────────────
  - hardware/alsa-utils.bst
  - hardware/wireplumber-pcsp.bst
  - hardware/usbmuxd.bst
  - hardware/ifuse.bst
  - hardware/brlaser.bst
  - hardware/lm-sensors.bst
  - hardware/ddcutil.bst

  # ── input and fonts ──────────────────────────────────────────────────
  # IBus Rime input method; users select their own input sources.
  - input/ibus-rime.bst
  - fonts/nerd-fonts-symbols.bst

  # ── virtualization and containers ────────────────────────────────────
  - virt/virtualization.bst
  - virt/distrobox.bst
  - virt/nspawn.bst
  # VM guest agents; each starts only on its own hypervisor.
  - virt/qemu-guest-agent.bst
  - virt/hyperv-daemons.bst
  - freedesktop-sdk.bst:components/podman.bst
  - freedesktop-sdk.bst:components/skopeo.bst
  - freedesktop-sdk.bst:components/containers-common.bst

  # ── apps and CLI tools ───────────────────────────────────────────────
  - apps/ghostty.bst
  - apps/brew.bst
  - apps/brew-tarball.bst
  - apps/fastfetch.bst
  - apps/gum.bst
  - apps/tealdeer.bst
  - apps/ydotool.bst
  - apps/kanata.bst
  - gnome-build-meta.bst:freedesktop-sdk-extra.bst:components/just.bst
  - gnome-build-meta.bst:freedesktop-sdk-extra.bst:components/wl-clipboard.bst

  # ── developer tools ──────────────────────────────────────────────────
  - freedesktop-sdk.bst:components/buildstream2.bst
  - freedesktop-sdk.bst:components/flatpak-builder.bst
  - freedesktop-sdk.bst:components/git.bst
  - freedesktop-sdk.bst:components/git-lfs.bst
  - freedesktop-sdk.bst:components/debuginfod.bst

  # ── diagnostics ──────────────────────────────────────────────────────
  - diagnostics/powertop.bst
  - diagnostics/nethogs.bst
  - diagnostics/nicstat.bst
  - diagnostics/tiptop.bst
  - diagnostics/sysstat.bst
  - diagnostics/trace-cmd.bst
  - freedesktop-sdk.bst:components/bpf-maybe.bst
  - freedesktop-sdk.bst:components/dmidecode.bst
  - gnome-build-meta.bst:gnomeos-deps/bpftop.bst
  - gnome-build-meta.bst:freedesktop-sdk-extra.bst:components/numactl.bst

(?):
- arch == "x86_64":
    depends:
      (>):
      - hardware/intel-media-driver.bst
      # x86_64 only: the aarch64 kernel enables neither vmwgfx nor VMCI, so
      # display auto-resize, the reason to ship it, cannot work there yet.
      - virt/open-vm-tools.bst
