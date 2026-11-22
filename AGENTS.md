# Mercury agent guide

Mercury is a bootc OCI desktop image (niri + DankMaterialShell) assembled
from source with BuildStream 2. It is not an RPM-based image: do not use
`dnf`, `rpm-ostree`, COPRs, Containerfile package overlays, or post-build
package installation. Make image changes through BST elements.

Project skills live in `.agents/skills/` and are discovered by Pi and GitHub
Copilot. Load only the skill matching the task; do not read every skill.
Skills are named `mercury-*`; `mercury-desktop` covers the niri + DMS stack
(there are no GNOME Shell extensions).

## Factory model invariants

- **Scoped Documentation**: Correct durable, task-relevant guidance when the work reveals an error or missing constraint. Do not manufacture documentation changes for every session or expand a read-only task into writes. Preparing changes does not authorize committing or publishing them.
- **Docs Are the Model**: Skills and documentation are evergreen operating procedures. Never append dated session logs, running issue numbers, or resolved checklists. Codify learnings as timeless architectural invariants and failure modes.
- **Documentation Freshness**: Verify external syntax against current official documentation and cite the source when updating guidance. Direct official documentation is equally valid to Context7.

## Sources of truth

1. Read the file being changed and its callers before editing it.
2. Use the relevant `.agents/skills/` package for task-specific guidance.
3. Treat workflows, elements, the Justfile, and tests as current truth; prose
   that disagrees with executable configuration is stale.
4. Verify external syntax and behavior in current official documentation before
   changing BuildStream, bootc, GitHub Actions, cosign, or skopeo usage.

## Non-negotiable safety

- Do not post GitHub comments, reviews, or edit PR bodies unless explicitly
  asked.
- Never expose secrets or weaken signing, provenance, or supply-chain checks.
- Never push directly to `main`. Work on a feature branch and leave final
  approval and merge to a human.
- Pin third-party GitHub Actions to full commit SHAs with a version comment.

## Scope

Single x86_64 image, one rolling `:latest` stream. **No** aarch64, no NVIDIA
variant, no gaming variant, no stable/next promotion machinery. Do not
reintroduce variant matrices or multi-stream release plumbing.

## Development workflow

- `main` is the only branch; PRs target it.
- Run `just --list` before inventing maintenance commands. Add a Justfile
  recipe when a repeatable repository operation has no existing entry.
- Run `just validate` for BST or image changes. Use the narrowest additional
  check that exercises the change.
- Label a same-repo PR `build` to run the full CI build + boot test.
- Before claiming completion, inspect the diff and report the checks actually
  run. Do not claim CI is green while runs are pending or failing.
- Commits use `<type>(<scope>): <description>` and the repo-local
  `Assisted-by:` trailer, never `Co-authored-by:`.

## Architecture invariants

- BuildStream elements are the only package/build mechanism.
- OCI filesystem-producing layers use `kind: compose`; `kind: stack` only
  aggregates dependencies and produces no filesystem output.
- Cargo source blocks are generated with
  `python3 files/scripts/generate_cargo_sources.py <Cargo.lock>`.
- Patch junctions through `patch_queue`; do not edit staged junction contents.
- Keep install commands deterministic: no network access, timestamps, hostname,
  user identity, or mutable branch refs.
- `bst` runs in the pinned bst2 container — always use `just bst ...`, never
  a host bst.

## Human decision gates

Stop and ask before:

- architecture or new-subsystem decisions;
- user-visible behavior changes without agreed acceptance criteria;
- authentication, signing, secrets, or third-party supply-chain changes;
- final PR approval or merge.

## Agent skills

### Issue tracker

Issues live in GitHub Issues on `Siddhj2206/mercury` via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at the repo root, created lazily. See `docs/agents/domain.md`.
