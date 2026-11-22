# mercury-secure-boot (behind `ujust enroll-secure-boot-key`) and the boot
# service that keeps the ESP copies of the shim chain in step with the
# image, since bootc upgrades never touch the ESP. Signed images only; see
# mercury/secure-boot.bst.
kind: manual

build-depends:
- core/sandbox-tools.bst

# The boot layer stages these tools through mercury/secure-boot-tools-files.bst,
# without these dependencies; mercury/deps.bst puts them in the base and the
# final OCI elements fail if the base lacks what mercury-secure-boot runs.
depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- mercury/efibootmgr.bst
- gnome-build-meta.bst:freedesktop-sdk-extra.bst:components/mokutil.bst

variables:
  strip-binaries: ''

config:
  install-commands:
  - install -Dm755 mercury-secure-boot "%{install-root}/usr/libexec/mercury-secure-boot"
  - install -Dm644 mercury-secure-boot-update.service "%{install-root}/usr/lib/systemd/system/mercury-secure-boot-update.service"
  - mkdir -p "%{install-root}/usr/lib/systemd/system/multi-user.target.wants"
  - ln -s ../mercury-secure-boot-update.service "%{install-root}/usr/lib/systemd/system/multi-user.target.wants/mercury-secure-boot-update.service"

sources:
- kind: local
  path: files/secure-boot
