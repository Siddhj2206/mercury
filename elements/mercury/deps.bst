# Mercury's package manifest: generic tools and services layered over the
# freedesktop-sdk runtime. Desktop-session content lives in desktop/deps.bst
# and core services in system/deps.bst (see oci/layers/mercury-stack.bst).
# Add or remove image content via `.bst` elements here — never via
# dnf/RPM/Containerfile overlay logic.
kind: stack

depends:
  # IBus Rime input method; users select their own input sources.
  - mercury/ibus-rime.bst

  - mercury/brew.bst
  - mercury/brew-tarball.bst


  - mercury/ghostty.bst

  - mercury/fastfetch.bst
  - mercury/nerd-fonts-symbols.bst
  - mercury/gum.bst
  - mercury/tealdeer.bst
  - mercury/ydotool.bst
  - mercury/kanata.bst

  - mercury/zswap-config.bst
  - mercury/kexec-disable.bst
  - mercury/swapfile.bst
  - mercury/bootc-install-config.bst
  - mercury/composefs-loop-udisks-ignore.bst
  - mercury/udev-groups.bst

  - mercury/uutils-coreutils.bst
  - mercury/sudo-rs.bst
  - mercury/sudo-linuxbrew-path.bst
  - mercury/fprintd-system-auth.bst
  - mercury/fprintd-fingerprint-auth.bst
  - mercury/oo7-passwd-pam.bst
  - mercury/pam-u2f.bst
  # efibootmgr and mokutil stay in every image: the Secure Boot tools in
  # the boot layer (oci/layers/boot-stack.bst) run them but cannot carry them.
  - mercury/efibootmgr.bst
  - gnome-build-meta.bst:freedesktop-sdk-extra.bst:components/mokutil.bst
  - mercury/xdg-terminal-exec.bst
  - mercury/network.bst
  - mercury/nfs-utils.bst
  - mercury/networkmanager-polkit.bst
  - mercury/usbmuxd.bst
  - mercury/ifuse.bst
  - mercury/wireplumber-pcsp.bst
  - mercury/alsa-utils.bst
  - mercury/brlaser.bst
  - mercury/powertop.bst
  # - mercury/lsp-plugins-lv2.bst

  # Include things missing from the base image
  - gnome-build-meta.bst:core-deps/fwupd.bst

  - mercury/virtualization.bst

  - freedesktop-sdk.bst:components/buildstream2.bst
  - freedesktop-sdk.bst:components/containers-common.bst
  - freedesktop-sdk.bst:components/debuginfod.bst
  - freedesktop-sdk.bst:components/dmidecode.bst
  - freedesktop-sdk.bst:components/git-lfs.bst
  - freedesktop-sdk.bst:components/git.bst
  - freedesktop-sdk.bst:components/podman.bst
  - freedesktop-sdk.bst:components/skopeo.bst
  - freedesktop-sdk.bst:components/flatpak-builder.bst

  - freedesktop-sdk.bst:components/bpf-maybe.bst
  - gnome-build-meta.bst:gnomeos-deps/bpftop.bst

  - mercury/nicstat.bst
  - mercury/tiptop.bst
  - gnome-build-meta.bst:freedesktop-sdk-extra.bst:components/numactl.bst
  - mercury/sysstat.bst
  - mercury/trace-cmd.bst

  - mercury/distrobox.bst
  - mercury/nspawn.bst
  - gnome-build-meta.bst:freedesktop-sdk-extra.bst:components/just.bst
  - gnome-build-meta.bst:freedesktop-sdk-extra.bst:components/wl-clipboard.bst

  - mercury/bindmounts.bst

  # VM guest agents; each starts only on its own hypervisor.
  - mercury/qemu-guest-agent.bst
  - mercury/hyperv-daemons.bst

  - mercury/nethogs.bst
  - mercury/lm-sensors.bst
  - freedesktop-sdk.bst:components/which.bst
  - mercury/ddcutil.bst

(?):
- arch == "x86_64":
    depends:
      (>):
      - mercury/intel-media-driver.bst
      # x86_64 only: the aarch64 kernel enables neither vmwgfx nor VMCI, so
      # display auto-resize, the reason to ship it, cannot work there yet.
      - mercury/open-vm-tools.bst
