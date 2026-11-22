# CONTRIBUTING

Mercury is a personal, single-maintainer image — but sane drive-by PRs are
welcome.

## ⚠️ Mercury uses BuildStream 2 — not Containerfiles

Mercury is built with **[BuildStream 2](https://buildstream.build/)** (BST),
not a Containerfile or DNF/RPM like Bluefin/ublue images. There is no
package layer to edit; software changes are BST element changes.

Read [`AGENTS.md`](AGENTS.md) first — build instructions, BST workflow,
commit style, and mandatory gates live there.

## Prerequisites

- `podman` — required for BST sandbox execution
- `just` — `brew install just` or your OS package manager

BST itself runs inside the pinned `bst2` container — use `just bst ...`
rather than installing `bst` directly.

## Pull requests

- Open PRs against `main`
- Run `just validate && just lint` before opening a PR
- Follow [Conventional Commits](https://www.conventionalcommits.org/) for
  commit messages, with an `Assisted-by:` trailer (not `Co-authored-by:`)

## Where things live

```
project.conf          # BST project configuration
elements/             # BST element files (.bst) — one per package
patches/              # Patches applied to junction elements via patch_queue
files/                # Static files installed by elements
```

Full build reference and BST workflow: [`AGENTS.md`](AGENTS.md) and
[`docs/build.md`](docs/build.md).
