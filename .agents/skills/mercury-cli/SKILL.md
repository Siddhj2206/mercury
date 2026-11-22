---
name: mercury-cli
description: Author safe end-user recipes for the `mercury` command in files/system/shared/usr/share/mercury/justfile, including quoting, gum, JSON, and public-post confirmation.
metadata:
  context7-sources:
    - /bootc-dev/bootc
---

# Mercury User Recipes

`just <recipe>` is for developers and CI from the root repository `Justfile`.
`mercury <verb>` is for end users inside the booted image: `files/system/shared/usr/bin/mercury` is a thin wrapper that execs `just --justfile /usr/share/mercury/justfile`, whose source lives at `files/system/shared/usr/share/mercury/justfile`.

Existing verbs: `info`, `changelog`, `config-diff`, `refresh-config`, `report`, `confirm <issue>`, `verify [issue]`.

## When to Use

- Adding, editing, or testing end-user convenience recipes in `files/system/shared/usr/share/mercury/justfile`
- Modifying the data-donation verbs (`report`, `confirm`, `verify`) — see `docs/feedback-loop.md`
- Handling CLI interaction tools like Charm `gum`, desktop notifications, or system diagnostics

## When NOT to Use

- Editing repository-level developer commands in the root `Justfile` → load `mercury-buildstream`
- Modifying host Homebrew integration → load `mercury-workstation`
- Adding BST elements → load `mercury-packaging`

## Core Process

1. **Author Recipe**: Add or edit the recipe in `files/system/shared/usr/share/mercury/justfile`.
2. **Quote & Validate Arguments**: Pass all arguments through `quote()` and validate with bash regular expressions:
   ```just
   ISSUE={{ quote(issue) }}
   [[ "$ISSUE" =~ ^[1-9][0-9]*$ ]] || exit 2
   ```
3. **Check Recipe Parsing**: Parse the file with the Just version shipped in the target image: `just --justfile files/system/shared/usr/share/mercury/justfile --list`. Heredocs are allowed when their indentation and delimiters parse correctly. Prefer `jq -n` for constructing JSON.
4. **Guard Interactive Steps**: Ensure commands requiring a TTY fail closed when run in non-interactive environments:
   ```bash
   if [ ! -t 0 ]; then
       echo "Interactive terminal required" >&2
       exit 1
   fi
   ```
5. **Respect the Donation Boundary**: `report`, `confirm`, and `verify <issue>` publish user-owned data (gist or issue comment via the user's `gh` login) only after the user reviews and confirms. Never add a recipe that posts data publicly without an explicit, interactive confirmation.
6. **Rebuild & Verify**: The justfile and wrapper ship via the system layer; validate with `just validate` and build the composing element.

## Invariants

- **Mandatory Quoting**: Just interpolates recipe arguments textually before bash parses them. Every parameter MUST pass through `{{ quote(...) }}` to prevent shell injection.
- **Fail Closed Without TTY**: Any recipe posting data publicly (e.g. creating GitHub issues or gists) must fail closed when stdin is not a terminal. Never treat a failed `gum confirm` or empty `read` as affirmative consent.
- **No bootc mutations without consent**: `report` collects read-only state; recipes must not run `bootc switch`/`upgrade`/package installs as a side effect.
- **Non-Interactive Sudo**: Use `sudo -n` for status checks so scripted recipe execution does not hang waiting for a password prompt.
- **Version-Specific Parsing**: Check the target image's Just version and test both Just parsing and the rendered shell syntax before changing valid heredocs — older Just versions had heredoc parsing problems, but that is not a blanket prohibition.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The argument is just a number, so quoting isn't strictly necessary." | Unquoted arguments allow arbitrary shell token expansion if malformed input is passed. |
| "A heredoc parsed on my host, so it works everywhere." | Validate with the target image's Just version and preserve literal shell/JSON quoting. |
| "Users only run `mercury` in terminal windows." | Scripts and background services can invoke it; non-TTY safety must always be guarded. |

## Red Flags

- Unquoted recipe arguments: `{{ arg }}` instead of `{{ quote(arg) }}`
- Heredoc delimiters or indentation that fail parsing with the target image's Just version
- Missing non-interactive guards on destructive or public-posting commands
- A recipe that files issues, gists, or comments without an explicit user confirmation
- Modifying the root `Justfile` when a user-facing `mercury` command was requested

## Verification

- [ ] Every interpolated argument is wrapped in `{{ quote(...) }}`
- [ ] Argument syntax validation is enforced in shell
- [ ] Recipe exits with code != 0 when run non-interactively without required flags
- [ ] The recipe file parses with the target image's Just version; rendered shell syntax is valid
- [ ] `just validate` passes

## References

- [`files/system/shared/usr/share/mercury/justfile`](../../../files/system/shared/usr/share/mercury/justfile)
- [`files/system/shared/usr/bin/mercury`](../../../files/system/shared/usr/bin/mercury)
- [`docs/feedback-loop.md`](../../../docs/feedback-loop.md)
