# dsearch (dux-search) — filesystem search engine for the DMS launcher.
# Upstream release binary + the user unit from the repo's assets/.
kind: manual

sources:
- kind: remote
  (?):
  - arch == "x86_64":
      url: https://github.com/duxlabs-dev/dux-search/releases/download/v2.1.1/dsearch-linux-amd64.gz
      ref: fe4f510808a565660d0de73f4a66dffc3293178ee728ed0a0d37cc611d41c77f
  - arch == "aarch64":
      url: https://github.com/duxlabs-dev/dux-search/releases/download/v2.1.1/dsearch-linux-arm64.gz
      ref: b5e65bc630b6f2afbb23a899a56704ef9a0308bf8b4412e20e52e86ffecafb39
  directory: bin
  # TODO: bst track

- kind: remote
  url: https://raw.githubusercontent.com/duxlabs-dev/dux-search/v2.1.1/assets/dsearch.service
  ref: 98c06c988bc39d2c2d089fd386bacd215be5968b2ae9c3b559ae49979657ca68
  directory: conf

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/gzip.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

config:
  install-commands:
  - gunzip -c bin/dsearch-linux-*.gz > dsearch
  - install -Dm755 dsearch "%{install-root}%{bindir}/dsearch"
  - install -Dm644 conf/dsearch.service "%{install-root}%{indep-libdir}/systemd/user/dsearch.service"
  - "%{install-extra}"
