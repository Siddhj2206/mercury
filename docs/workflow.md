# Community workflow

Mercury is a personal, single-maintainer project. There is no Prow, no OWNERS
hierarchy, no triage team — issues and PRs are plain GitHub.

## Issue flow

`filed → triaged → fixed (or wontfix)`

- `report: attached` means a diagnostic bundle from `ujust report` is present.
  Read it before asking for more logs.
- `ujust confirm` adds another hardware instance without a duplicate issue.
- `ujust verify` adds post-fix evidence on real hardware.

### Data donation pattern

`ujust report` is a deliberate data donation. The Report a Problem app shows
the scrubbed payload before anything is published, then files the issue with
the user's `gh` login (a secret gist only when GitHub refuses the artifact).
That is not telemetry. See [feedback-loop.md](feedback-loop.md).

## Branch and stream model

Single branch: `main`. Single stream: `:latest`.

```text
PR to main
  → validate.yml (static checks)
  → build label → build.yml (BST build → chunkify → lint → boot test)

merge to main
  → build.yml
      ├─ :<sha>
      ├─ :latest
      └─ :VERSION.DATE
```

All PRs target `main`. Fork PRs cannot get the `build` label path — ask the
maintainer to cherry-pick to a same-repo branch when a full CI build is
needed.

```bash
# Branch from main
git checkout origin/main -b feat/my-change

# Work, validate, commit
just validate
git commit -m "feat(mercury): ..."

# Push and open PR
gh pr create --repo Siddhj2206/mercury --base main
```

## References

- [freedesktop-sdk](https://gitlab.com/freedesktop-sdk/freedesktop-sdk)
- [gnome-build-meta](https://github.com/GNOME/gnome-build-meta)
- [Mercury issues](https://github.com/Siddhj2206/mercury/issues)
- Upstream lineage: [projectbluefin/dakota](https://github.com/projectbluefin/dakota)
