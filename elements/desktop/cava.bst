# cava — console audio visualizer; optional DMS dependency (audio widget
# reads its raw output over pipewire). Graphical outputs (ncurses, SDL) are
# unnecessary for DMS and left to autodetection.
kind: autotools

sources:
- kind: tar
  url: https://github.com/karlstav/cava/releases/download/1.0.0/cava-1.0.0.tar.gz
  ref: 603c6af87a4bd100a171dad1c657364b914d172eca1a27a6f18a71ea586056cc
  # TODO: bst track

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-autotools.bst
- freedesktop-sdk.bst:components/pkg-config.bst
- freedesktop-sdk.bst:components/fftw.bst
- desktop/iniparser.bst
- freedesktop-sdk.bst:components/pipewire.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/fftw.bst
- desktop/iniparser.bst
- freedesktop-sdk.bst:components/pipewire.bst
