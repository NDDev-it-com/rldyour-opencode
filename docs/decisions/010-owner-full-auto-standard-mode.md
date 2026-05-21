# ADR-010: Owner full-auto standard mode

- Status: accepted
- Date: 2026-05-21
- Deciders: @rldyourmnd
- Supersedes: ADR-009

## Context and Problem Statement

The owner has made an explicit product policy decision: YOLO mode, full-auto
mode, and dangerously-skip-permissions mode are the standard operating posture
for the AI CLI toolchain. The OpenCode adapter is an owner-controlled
configuration repository for the maintainer's trusted workflow.

OpenCode's permission model supports primary-context `allow`, `ask`, and
`deny` values. This repository must encode the owner's standard directly in
the published adapter configuration instead of relying on an out-of-repo local
override.

## Decision Drivers

- The owner explicitly requires full-auto mode to be standard.
- The primary `build` and `plan` contexts are implementation and planning
  surfaces for the owner's trusted local workflow.
- Dynamic high-impact shell blocking is already implemented through
  `tool.execute.before` in `ry-shell-strategy`.
- `permission.ask` remains unsuitable for enforcement because it was
  typed-but-untriggered in the audited OpenCode runtime surface.

## Decision Outcome

`opencode.json` publishes owner-standard full-auto primary permissions:

```json
"permission": {
  "edit": "allow",
  "bash": "allow"
}
```

The `build` and `plan` primary agents also use `edit: "allow"` and
`bash: "allow"`.

Reviewer subagents keep their report-only restrictions (`edit: "deny"` plus
read-only git bash allowlists) because their role contract is review, not
implementation. This role scoping is not a safe-mode default for the primary
runtime.

## Consequences

Positive:

- The repository now matches the owner's operating standard without requiring
  a separate local overlay.
- Contract validation can prove the intended posture instead of relying on
  prose.
- The dynamic guardrail layer remains independent from prompt-based permission
  approval flows.

Negative:

- Running the published primary configuration on shared or untrusted machines
  has higher operational risk. That is outside the intended owner-controlled
  environment.

## Compliance

- `references/rldyour-contract.json` records `full_auto_standard: true`.
- `scripts/validate_contract.py` fails if top-level, `build`, or `plan`
  primary permissions drift away from `edit: "allow"` and `bash: "allow"`.
- `scripts/check_plugin_hooks.py` still rejects `permission.ask` as an
  enforcement hook.
- `scripts/tests/test_validate_contract.py` locks the full-auto contract.
