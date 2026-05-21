# ADR-006: Dynamic shell guard coverage for dangerous bash patterns

- Status: accepted
- Date: 2026-05-17
- Updated: 2026-05-20
- Deciders: @rldyourmnd
- Consulted: ChatGPT 5.5 Pro audit prompt (2026-05-17) + three deep-audit reports + OpenCode v1.15.4 source inspection

## Context and Problem Statement

The marketplace uses owner-standard full-auto OpenCode permissions for primary
contexts and one runtime-proven dynamic layer for dangerous bash patterns:

- `.opencode/plugins/ry-shell-strategy.ts` subscribes to `tool.execute.before` and throws unconditionally when a dangerous pattern is detected. The throw fires while the repository default has `bash: "allow"`, so the guardrail is independent of OpenCode permission prompts.
- `.opencode/plugins/ry-permission-events.ts` subscribes to the generic `event` hook and logs `permission.asked` / `permission.replied`. It is observability-only and never enforces policy.

Before the 2026-05-20 hardening worktree, the marketplace also shipped `.opencode/plugins/ry-permission-policy.ts` on the typed `permission.ask` hook. A 2026-05-20 source inspection of OpenCode v1.15.4 found that the permission service publishes `permission.asked` / `permission.replied` bus events, but no runtime path triggers the plugin-level `permission.ask` hook. Treating that typed-but-untriggered hook as a security boundary was incorrect, so enforcement was consolidated into the runtime-proven `tool.execute.before` layer.

Additionally, the force-push throw in `ry-shell-strategy.ts` toasted-then-threw but did not call `client.app.log("error", ...)` before throwing, so an audit operator inspecting the server log saw no record of the block.

## Decision Drivers

- The primary `build` and `plan` agents now run with `bash: allow`; the unconditional `tool.execute.before` layer remains the deterministic dynamic safety net for dangerous patterns.
- OpenCode v1.15.x subagent permission inheritance is still partial (PR `sst/opencode#24293` open); we cannot assume `deny` rules propagate to child sessions reliably.
- The SDK type surface alone is not sufficient proof that a hook is triggered. Security boundaries must use documented or source-proven runtime hooks.
- Audit trail completeness: every block must record a `service: <plugin>, level: error` line in `client.app.log` before the throw, so log analysis is sufficient to reconstruct what happened.

## Considered Options

1. Rely on `permission.ask` only. Reject: it does not cover `bash: allow`, and in pinned OpenCode v1.15.4 it is not triggered by the permission service.
2. Keep `permission.ask` as a secondary deny layer. Reject: retaining dead enforcement creates false confidence and makes audits believe a non-firing hook is protecting the system.
3. Use owner-standard full-auto static permission config, use `tool.execute.before` as the deterministic dynamic deny layer for high-impact dangerous patterns, and keep permission bus events as observability only. **Selected.**

## Decision Outcome

`ry-shell-strategy.ts` enforces three dangerous patterns:

| Pattern | `tool.execute.before` behavior | Test |
|---|---|---|
| `git push --force` / `-f` without `--force-with-lease` | throw | `test_shell_strategy_regexes.py` |
| `rm -rf` targeting `/` / `$HOME` / `~` / cwd / parent dir (allowlist: `node_modules`) | throw | `test_shell_strategy_regexes.py` |
| `git push --no-verify` on any branch | throw unless `RY_ALLOW_NO_VERIFY=1` | `test_shell_strategy_regexes.py` |

Each throw emits `log("error", "<msg> cmd=<truncated 200 chars>")` BEFORE the `toast("error", ...)` and `throw new Error(...)`. The log call uses `client.app.log` (server log) so the audit trail records the block reason even when the TUI toast call fails silently.

The plugin uses flag-boundary regex helpers (`(?<![A-Za-z0-9-])--FLAG(?![A-Za-z0-9-])`) to avoid the `\b--FLAG\b` silent-match bug (fixed in 0.10.1). The boundaries also distinguish `--force` from `--force-with-lease` (the latter is the SAFE form).

`node_modules` cleanup is the documented allowlist exception: recursive deletion of a `node_modules` tree is a legitimate developer operation.

## Consequences

Positive:

- Build / plan / reviewer subagent profiles all benefit from the same dangerous-pattern coverage.
- Audit trail is complete: every block has a structured server-log entry before the user-visible toast.
- The hook surface is validated by `scripts/check_plugin_hooks.py`; `permission.ask` cannot return as a hidden security boundary without failing CI.
- Regex semantics are covered by `test_shell_strategy_regexes.py`.

Negative:

- The unconditional throw can frustrate operators who want to perform a legitimate destructive operation. Mitigation: the throw message says exactly what the safe replacement is (`--force-with-lease` for force-push; specific paths instead of root targets for `rm -rf`).

## Compliance

- The 2026-05-20 hardening worktree consolidates dynamic enforcement into `ry-shell-strategy.ts` and removes `permission.ask` from the security path.
- `scripts/tests/test_shell_strategy_regexes.py` locks the regex semantics.
- `scripts/check_plugin_hooks.py` rejects `permission.ask` and event-type strings used as top-level plugin hooks.
- `scripts/tests/test_plugin_surface.py::test_no_console_log_in_plugin_production_code` enforces the `client.app.log` migration on every plugin.

## Future work

- If a future OpenCode release proves a permission interception hook is triggered before user prompts, this ADR can be revisited. Until then, permission event handling remains observability-only.
