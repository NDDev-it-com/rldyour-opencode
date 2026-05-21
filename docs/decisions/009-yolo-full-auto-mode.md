# ADR-009: Superseded safe-public and owner-local permission split

- Status: superseded by ADR-010
- Date: 2026-05-18
- Updated: 2026-05-21
- Deciders: @rldyourmnd

## Context

ADR-009 originally selected a safe public default with owner-local full-auto
overrides. That decision was based on the May 2026 audit recommendation to
avoid publishing broad `edit: "allow"` and `bash: "allow"` defaults.

On 2026-05-21, the owner issued a direct policy decision that YOLO mode,
full-auto mode, and dangerously-skip-permissions mode must be available as the
standard posture across all AI CLI tool adapters.

## Supersession

ADR-010 supersedes this ADR. The OpenCode adapter now publishes owner-standard
full-auto permissions for top-level, `build`, and `plan` primary contexts.

The non-superseded part of the old decision remains: `permission.ask` must not
be used as a security boundary. Dynamic blocking stays in
`tool.execute.before` through `ry-shell-strategy`.
