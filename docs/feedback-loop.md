# Mercury Feedback Loop

Mercury keeps dakota's core idea: every user report is a structured piece of
evidence, not a ticket to triage from scratch. There is no telemetry and no
phone-home — every piece of data is donated by a human who reviews it first.

## The data donation principle

A `ujust report` submission is a deliberate, informed data donation. The
Report a Problem app shows the scrubbed payload for review before the issue
is filed, then publishes it with the user's `gh` login (a secret gist only
when GitHub refuses the artifact). The user controls what leaves their
machine. This is not telemetry.

## The three verbs

| Command | What it does |
|---|---|
| `ujust report` | Captures system state, shows the report, files the issue. One command instead of a wall of "please attach logs." |
| `ujust confirm <issue>` | Adds a hardware fingerprint to an existing issue — same bug, different hardware, no duplicate filing. |
| `ujust verify <issue>` | After a fix ships in `:latest`, confirms it works on that machine. Closes the loop with evidence. |

`report: attached` on an issue means full structured evidence is already
available — do not ask the reporter to re-describe what the report contains.

## Evidence by role

| Who | Command | Evidence produced |
|---|---|---|
| User | `ujust report` / `confirm` / `verify` | System state, hardware fingerprints, post-fix attestation |
| Contributor | `just validate` / `just build` / `just boot-test` / `just lint` | Buildable graph, booting image, lint-clean image |
| CI | `validate.yml`, `build.yml` | PASS/FAIL on PR; published `:sha`, `:latest`, `:VERSION.DATE` |

## Design rules

1. **Evidence is always user-owned.** Reports belong to the user who filed
   them. Nothing is aggregated into a central database.
2. **The Justfile is the single source of truth.** Every verification step is
   a `just` or `ujust` command — no loose shell incantations.
3. **CI supplements, never replaces, hardware feedback.** Automated boot
   tests run in QEMU; users have real hardware with real variance.
4. **Agents produce the same evidence as humans.** An agent claiming an issue
   runs the same `just validate → build → boot-test → lint` pipeline.

## Related

- [AGENTS.md](../AGENTS.md) — contributor workflow and invariants
- [Justfile](../Justfile) — all commands (`just --list`)
