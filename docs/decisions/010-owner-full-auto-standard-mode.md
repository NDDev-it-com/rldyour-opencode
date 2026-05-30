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
- The owner-standard workflow deliberately lets agents inspect source and
  configuration files needed for implementation work. Broad read access is a
  feature of the trusted owner environment, not an accidental downgrade from
  OpenCode defaults.
- `permission.ask` remains unsuitable for enforcement because it was
  typed-but-untriggered in the audited OpenCode runtime surface.

## Decision Outcome

`opencode.json` publishes owner-standard full-auto primary permissions for
normal implementation work, including external-directory access and doom-loop
retry protection:

```json
"permission": {
  "read": "allow",
  "edit": "allow",
  "bash": "allow",
  "external_directory": "allow",
  "doom_loop": "allow"
}
```

The `build` and `plan` primary agents also use `edit: "allow"` and
`bash: "allow"` plus the same explicit full-auto permission posture for
OpenCode's canonical v1.15.x permission keys.

OpenCode's upstream default can deny sensitive env-file reads. This adapter
intentionally publishes `read: "allow"` for the owner-standard primary
runtime, and now also publishes `external_directory: "allow"` and
`doom_loop: "allow"` so the standalone adapter matches the owner's no-prompt
standard. The root `oc` launcher mirrors the same full-auto permissions through
`OPENCODE_CONFIG_CONTENT` for the trusted workstation. `ry-env-protection`
remains a runtime secret-exfiltration guardrail for obvious secret paths and
shell reads; it is not a replacement safe mode and must not be treated as a
prompt approval boundary.

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
- Static OpenCode default env-file denial is not the owner-standard boundary
  in this adapter. The boundary is trusted-owner execution plus explicit
  runtime guardrails and auditability.
- Standalone adapter sessions no longer preserve OpenCode's default
  external-directory and doom-loop prompts; the release-safe profile remains
  the conservative published example.

## Compliance

- `references/rldyour-contract.json` records `full_auto_standard: true`.
- `scripts/validate_contract.py` fails if top-level, `build`, or `plan`
  primary permissions drift away from the owner-standard permission contract.
- `scripts/validate_contract.py` fails if top-level, `build`, or `plan`
  permissions drift away from the documented no-prompt full-auto policy.
- `scripts/validate_contract.py` fails if top-level `read: "allow"` is present
  without the matching owner-read policy metadata and `ry-env-protection`
  `tool.execute.before` guardrail mapping.
- `scripts/check_plugin_hooks.py` still rejects `permission.ask` as an
  enforcement hook.
- `scripts/tests/test_validate_contract.py` locks the full-auto contract.
