kind: manual

# No external sources - all files are inline.
build-depends:
- build-tools/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  strip-binaries: ""

config:
  install-commands:
  - |
    install -Dm644 /dev/null "%{install-root}%{indep-libdir}/tmpfiles.d/mercury-network.conf"
    cat > "%{install-root}%{indep-libdir}/tmpfiles.d/mercury-network.conf" <<'EOF'
    # Symlink /etc/resolv.conf to systemd-resolved's stub resolver.
    # L+ removes any existing file (e.g. the empty placeholder from the base image)
    # so applications that read resolv.conf directly (Steam, Distrobox, etc.) get DNS.
    L+ /etc/resolv.conf - - - - /run/systemd/resolve/stub-resolv.conf
    EOF

  # NetworkManager manages the network. Mercury's presets have no catch-all
  # `disable *`, so preset-all would otherwise enable systemd-networkd too,
  # and systemd-networkd-wait-online then holds network-online.target until
  # its 2-minute timeout on every boot. Mirrors gnome-build-meta's
  # 80-network.preset, which Mercury does not import.
  - |
    install -Dm644 /dev/null "%{install-root}%{indep-libdir}/systemd/system-preset/80-mercury-network.preset"
    cat > "%{install-root}%{indep-libdir}/systemd/system-preset/80-mercury-network.preset" <<'EOF'
    enable NetworkManager.service
    disable systemd-networkd.service
    disable systemd-networkd.socket
    disable systemd-networkd-varlink.socket
    disable systemd-networkd-varlink-metrics.socket
    disable systemd-networkd-resolve-hook.socket
    disable systemd-networkd-persistent-storage.service
    disable systemd-networkd-wait-online.service
    EOF

  - |
    install -Dm644 /dev/null "%{install-root}%{sysconfdir}/hosts"
    cat > "%{install-root}%{sysconfdir}/hosts" <<'EOF'
    127.0.0.1   localhost
    ::1         localhost
    EOF
