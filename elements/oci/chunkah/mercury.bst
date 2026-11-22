# Chunkah ownership for the exact default compose artifact, without replaying it.
kind: chunkah-ownership

build-depends:
  - oci/layers/mercury.bst
  - oci/layers/mercury-stack.bst
  - oci/layers/brew-toolchain.bst
  - oci/chunkah/brew-toolchain.bst

config:
  layer-dependency: oci/layers/mercury.bst
  provenance-dependencies:
    - oci/layers/mercury-stack.bst
    - oci/layers/brew-toolchain.bst
  metadata-dependencies:
    - oci/chunkah/brew-toolchain.bst
  inherit-from-components:
    - oci/layers/brew-toolchain.bst
