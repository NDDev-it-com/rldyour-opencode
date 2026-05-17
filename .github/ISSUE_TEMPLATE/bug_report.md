---
name: Bug report
about: Report a defect in plugins, scripts, validators, or documentation
title: "[bug] "
labels: ["bug"]
assignees: ["rldyourmnd"]
---

## What is broken

<!-- One paragraph: the unexpected behaviour. -->

## Expected behaviour

<!-- What should happen instead, and the source-of-truth file that says so
(AGENTS.md line / ADR / reference doc). -->

## Reproduction steps

1.
2.
3.

## Environment

- OpenCode version: `opencode --version`
- `@opencode-ai/plugin` pin from `.opencode/package.json`:
- OS (Ubuntu / macOS / other):
- Bun version: `bun --version`
- Python version: `python3 --version`
- `git log -1 --oneline` of the affected checkout:

## Diagnostic evidence

Please attach:

- [ ] Output of `bash scripts/validate_config.sh`
- [ ] Output of `python3 -m pytest scripts/tests/ -v -k <relevant_test>` (if a specific test reproduces the issue)
- [ ] Output of `bash scripts/collect_diagnostics.sh --include-doctor` (post-sanitization)
- [ ] Relevant `client.app.log` entries from `~/.local/share/opencode/log/*.log`

## Additional context

<!-- Stack trace, console output, screenshots, related PRs. -->
