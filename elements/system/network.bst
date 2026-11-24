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

  - |
    install -Dm644 /dev/null "%{install-root}%{sysconfdir}/hosts"
    cat > "%{install-root}%{sysconfdir}/hosts" <<'EOF'
    127.0.0.1   localhost
    ::1         localhost
    EOF
