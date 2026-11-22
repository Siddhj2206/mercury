---
name: mercury-image
description: OCI layer assembly, boot layer and Secure Boot boundary, boot testing, VM work, and local OTA verification for Mercury images.
metadata:
  context7-sources:
    - /bootc-dev/bootc
---

# Mercury Image Integration

Use this skill when filesystem content crosses from BuildStream artifacts into OCI layers, or when testing and booting a local Mercury image.

## When to Use

- Modifying layer composition under `elements/oci/layers/`
- Changing post-install integration steps in `elements/oci/mercury-base.bst`, the boot layer (`oci/layers/boot.bst`), or the final element (`oci/mercury.bst`) — see `docs/oci-assembly.md`
- Running local VM boot tests (`just boot-test`, `just boot-fast`, `just boot-vm`)
- Validating transactional OTA updates or testing local registries (`references/local-ota.md`)

## When NOT to Use

- Building individual source packages or libraries → load `mercury-packaging`
- Desktop session stack (niri, DMS, greetd) → load `mercury-desktop`
- Modifying GitHub Actions CI export or publication → load `mercury-ci`
- Cosign verification or Secure Boot signing policy → load `mercury-release`

## Core Process

1. **Layer Composition**: Compose layers with `kind: compose`. Build dependencies define layer contents.
2. **Order Post-Install Steps**:
   - `systemd-sysusers --root /layer`
   - `glib-compile-schemas /layer/usr/share/glib-2.0/schemas`
   - `dconf update /layer/etc/dconf/db`
   - `ldconfig -r /layer` (must run LAST before `build-oci`)
3. **Respect the Boot Layer Boundary** (see `docs/oci-assembly.md`): the published image is `oci/mercury-base.bst` plus `oci/layers/boot.bst` appended via `scripts/oci_append_layer.py`. The boot layer holds everything gated by `secure_boot_signing` — kernel, modules, initramfs, depmod index, shim chain, signed EFI binaries, `lockdown=integrity` karg. The base must have the same cache key with and without `-o secure_boot_signing true`.
4. **Validate**: Run `just validate` to verify the composition graph.
5. **Boot Verification Ladder**:
   - Level 1: `just validate` (graph structure)
   - Level 2: `just lint` (`bootc container lint`)
   - Level 3: `just boot-test` (automated headless smoke test — graphical.target, `bootc status`, no zram)
   - Level 4: `just boot-fast` (interactive ephemeral VM via bcvk + virtiofs)
   - Level 5: Local OTA testing (`references/local-ota.md`) for hardware verification

## Invariants

- **Layer Element Kind**: All layer elements in `elements/oci/layers/` MUST use `kind: compose`. `kind: stack` produces empty artifacts and will break filesystem generation.
- **Linker Cache Load-Bearing Invariant**: `ldconfig -r /layer` must execute after all library updates and before `build-oci`. Any command altering `/usr/lib` must precede `ldconfig`.
- **No Kernel Modules in the Base**: The base elements fail on files under `/usr/lib/modules`, `/usr/lib/depmod.d`, `/etc/depmod.d`. Elements installing modules need a `kernel-modules` split the base compose excludes.
- **Boot Layer Adds Only Allowed Paths**: `oci_append_layer.py` + `ownership_metadata.py finalize-overlay` reject whiteouts, paths outside `--allow-prefix`, and changes to base paths. Base post-install steps never see the boot layer — nothing needing sysusers, ldconfig, schemas, or presets may live there.
- **Evidence Before Assertion**: Never assert boot success without executing one of the boot test recipes.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The element built, so the layer is fine." | Build success does not guarantee runtime inclusion or correct compose filters. |
| "I can put `ldconfig` anywhere in the post-install list." | If run before steps that copy libraries, `/etc/ld.so.cache` will be stale on boot. |
| "Booting in QEMU isn't necessary for a small change." | Session regressions (greeter loop, failed graphical.target) only manifest at real boot. |
| "I'll drop a module-loading config into the base layer." | Modules and depmod config belong to the signed boot layer; a base copy breaks `lockdown=integrity`. |

## Red Flags

- `kind: stack` inside `elements/oci/layers/`
- New post-install commands inserted after `ldconfig -r /layer`
- Kernel modules, depmod config, or Secure Boot artifacts added to the base layer
- Using `rpm-ostree` or `dnf` in layer integration scripts
- Boot-layer paths outside the `--allow-prefix` list in `oci_append_layer.py`

## Verification

- [ ] `just validate` passes
- [ ] `just lint` passes on the exported container
- [ ] `just boot-test` exits 0 (graphical.target reached)
- [ ] `/etc/ld.so.cache` contains newly introduced shared libraries
- [ ] Base cache key is identical with and without `-o secure_boot_signing true`

## References

- [`docs/oci-assembly.md`](../../../docs/oci-assembly.md)
- [`references/local-ota.md`](references/local-ota.md)
- [`elements/oci/`](../../../elements/oci/)
