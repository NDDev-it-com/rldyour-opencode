# ADR-009: Safe public and owner-local permission profiles

- Status: accepted
- Date: 2026-05-18
- Updated: 2026-05-21
- Deciders: @rldyourmnd
- Consulted: external audit (2026-05-17 archive review), Phase 0+1+2 fixes, cross-adapter audit (2026-05-21)

## Context and Problem Statement

The marketplace is published as a reusable OpenCode configuration repository,
but the owner also uses it locally as a high-velocity trusted-machine setup.
Those are different trust boundaries and must not share the same default
permission posture.

The audit (2026-05-17) flagged the global `edit: "allow"` / `bash: "allow"`
profile as "broad" and suggested a granular bash allowlist:

```json
"bash": {
  "*": "ask",
  "git status*": "allow",
  "git diff*": "allow",
  "rm *": "deny",
  "git push --force*": "deny"
}
```

Earlier versions accepted global `edit: "allow"` / `bash: "allow"` as the
default because the repository was owner-local. The 2026-05-21 cross-adapter
audit raised the correct governance issue: a public adapter should ship with a
safe baseline and let the owner add full-auto behavior through a personal local
override.

## Decision Drivers

- The public repository can be cloned by operators outside the owner's machine.
- OpenCode's documented defaults are permissive, so this repository must set
  explicit safe values instead of relying on defaults.
- Plugin guardrails already cover the high-impact dangerous patterns:
  - `ry-shell-strategy.ts` unconditionally blocks force-push-without-lease,
    catastrophic `rm -rf` targets, and `git push --no-verify` (Phase 1
    widened the block to any branch, with `RY_ALLOW_NO_VERIFY=1` opt-out).
  - `permission.ask` is not part of the security boundary. OpenCode v1.15.4
    exposes it in SDK types but does not trigger it from the permission
    service; `scripts/check_plugin_hooks.py` rejects it in plugin code.
  - `ry-env-protection.ts` blocks reads of `.env*`, `.pem`, `.key`, `.ssh/`,
    `.gnupg/`, `.aws/`, and credential-shaped paths through both `read`
    and `bash` tools, with data-movement (cp/mv/tar/zip/base64) detection
    added in Phase 1.
- The owner can still run full-auto through a personal config layer on a
  trusted machine, where that trade-off is explicit and local.

## Considered Options

1. **Safe public default + owner-local override.** **Selected.** The repository
   default asks before edits and shell commands; the owner may keep a personal
   full-auto layer outside the repository.
2. **No plugin guardrails, raw `allow` everywhere.** Reject. The catastrophic
   patterns (force-push, `rm -rf /`, `--no-verify` on product branches) need
   deterministic dynamic blocking even in a YOLO profile.
3. **Public YOLO `allow` + `tool.execute.before` guardrails.** Reject. Dynamic
   guardrails are defense-in-depth, not a substitute for safe public defaults.

## Decision Outcome

`opencode.json` publishes the safe baseline:

```json
"permission": {
  "edit": "ask",
  "bash": "ask",
  "webfetch": "allow",
  "websearch": "allow",
  "lsp": "allow",
  "skill": "allow",
  "glob": "allow",
  "grep": "allow",
  "read": "allow"
}
```

The `build` primary agent also uses `edit: "ask"` and `bash: "ask"`.
Reviewer subagents remain stricter (`edit: "deny"`, restricted read-only bash
allowlists).

Owner-local full-auto is not published as the repository default. Operators who
need it can layer their own user config or project-local override on a trusted
machine. The security boundary for the public repository is now **static
permission config + `tool.execute.before` guardrails**.

- AGENTS.md § Engineering Rules (existing policy text).
- AGENTS.md § CI/CD and Git Mutation Gate (added in Phase 1; prevents
  the agent from silently mutating remote state without user opt-in).
- `docs/security/mcp-trust-boundaries.md` (per-MCP trust classes).
- This ADR (the explicit safe-default / owner-override split).

## Consequences

Positive:

- Public clones start from a safer default that matches OpenCode's permission
  model: writes and shell commands require explicit approval.
- Owner full-auto remains possible without encoding that posture into the
  public artifact.
- Reviewer subagents keep their `edit: "deny"` profile, so read-only review
  workflows remain stricter than primary implementation workflows.

Negative:

- Routine owner workflows may pause for `edit` or `bash` approvals unless the
  owner installs a personal override.
- A user-local override is outside repository validation, so diagnostics should
  ask operators to disclose local config when debugging permission behavior.

## Compliance

- `scripts/tests/test_shell_strategy_regexes.py` locks the plugin guardrail
  behavior.
- `scripts/check_plugin_hooks.py` prevents typed-but-untriggered hook surfaces
  from being reintroduced as security boundaries.
- `scripts/tests/test_plugin_surface.py` enforces the no-`console.log`
  and audit-trail invariants.
- This ADR is referenced from README and security docs so external reviewers
  find the safe-default decision before re-litigating the permission model.

## Future work

- If OpenCode gains a first-class full profile/overlay mechanism, add a
  checked-in owner-mode example that is clearly not loaded by default.
- If OpenCode upstream lands first-class sandboxing (process isolation,
  filesystem container), evaluate switching the global default to that
  sandbox instead of plugin guardrails.
