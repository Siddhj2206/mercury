kind: script

build-depends:
  - gnome-build-meta.bst:freedesktop-sdk.bst:components/oci-builder.bst
  - filename: oci/layers/python-minimal.bst
    config:
      location: /layer

config:
  commands:
    - |
      cd /layer
      oci-builder \
        --name ghcr.io/siddhj2206/python-minimal \
        --entrypoint /usr/bin/python3 \
        . /oci-image
