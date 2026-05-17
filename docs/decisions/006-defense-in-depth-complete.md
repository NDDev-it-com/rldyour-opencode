# ADR-006: Defense-in-depth coverage for dangerous bash patterns

- Status: accepted
- Date: 2026-05-17
- Deciders: @rldyourmnd
- Consulted: ChatGPT 5.5 Pro audit prompt (2026-05-17) + three deep-audit reports

## Context and Problem Statement

The marketplace publishes two plugin layers that guard dangerous bash patterns:

- `.opencode/plugins/ry-shell-strategy.ts` subscribes to `tool.execute.before` and throws unconditionally when a dangerous pattern is detected. The throw fires regardless of whether the bash permission is statically `"allow"` (Build agent) or `"ask"` (plan + reviewer subagents).
- `.opencode/plugins/ry-permission-policy.ts` subscribes to `permission.ask` and sets `output.status = "deny"` for the same patterns. This hook only fires when the static permission is `"ask"`.

Before this release, only `ry-permission-policy.ts` covered all three documented patterns (force-push without lease, catastrophic `rm -rf`, `git push --no-verify` on product branches). `ry-shell-strategy.ts` threw only for force-push and merely warned for catastrophic `rm -rf` and ignored `--no-verify`. Result: under the Build agent's `bash: allow` profile, two of the three patterns reached the user's shell without any block — the deny-only `permission.ask` hook does not fire on `allow`.

Additionally, the force-push throw in `ry-shell-strategy.ts` toasted-then-threw but did not call `client.app.log("error", ...)` before throwing, so an audit operator inspecting the server log saw no record of the block.

## Decision Drivers

- The Build agent runs with `bash: allow` globally, so the unconditional `tool.execute.before` layer is the only safety net for that profile.
- OpenCode v1.15.x subagent permission inheritance is still partial (PR `sst/opencode#24293` open); we cannot assume `deny` rules propagate to child sessions reliably.
- Audit trail completeness: every block must record a `service: <plugin>, level: error` line in `client.app.log` before the throw, so log analysis is sufficient to reconstruct what happened.

## Considered Options

1. Rely on `permission.ask` only. Reject — does not cover `bash: allow`.
2. Rely on `tool.execute.before` only. Reject — pre-dialog denial in `permission.ask` is still useful for `bash: ask` profiles because it avoids the user dialog entirely for categorically dangerous patterns.
3. Keep both layers, with identical pattern coverage on both surfaces, and assert the coverage in tests. **Selected.**

## Decision Outcome

Both plugins now enforce the same three dangerous patterns:

| Pattern | Layer 1 (`tool.execute.before`, unconditional) | Layer 2 (`permission.ask`, deny-only) | Test |
|---|---|---|---|
| `git push --force` / `-f` without `--force-with-lease` | throw | deny | `test_permission_policy_regexes.py` |
| `rm -rf` targeting `/` / `$HOME` / `~` / cwd (allowlist: `node_modules`) | throw | deny | `test_permission_policy_regexes.py` |
| `git push --no-verify` on `main`/`master`/`release`/`production` | throw | deny | `test_permission_policy_regexes.py` |

Each throw on Layer 1 emits `log("error", "<msg> cmd=<truncated 200 chars>")` BEFORE the `toast("error", ...)` and `throw new Error(...)`. The log call uses `client.app.log` (server log) so the audit trail records the block reason even when the TUI toast call fails silently.

Both plugins use the same flag-boundary regex helpers (`(?<![A-Za-z0-9-])--FLAG(?![A-Za-z0-9-])`) to avoid the `\b--FLAG\b` silent-match bug (fixed in 0.10.1). The boundaries also distinguish `--force` from `--force-with-lease` (the latter is the SAFE form).

`node_modules` cleanup is the documented allowlist exception in both layers — recursive deletion of a `node_modules` tree is a legitimate developer operation.

## Consequences

Positive:

- Build / plan / reviewer subagent profiles all benefit from the same dangerous-pattern coverage.
- Audit trail is complete: every block has a structured server-log entry before the user-visible toast.
- Test parity between the two layers is enforced by 44 cases in `test_permission_policy_regexes.py`.

Negative:

- Two layers means two places to update when a new pattern is added. Mitigation: the test suite enforces lockstep coverage.
- The unconditional throw can frustrate operators who want to perform a legitimate destructive operation. Mitigation: the throw message says exactly what the safe replacement is (`--force-with-lease` for force-push; specific paths instead of root targets for `rm -rf`).

## Compliance

- 0.11.0 group B implements the symmetric layering.
- `scripts/tests/test_permission_policy_regexes.py` (44 cases) locks the regex semantics on both surfaces.
- `scripts/tests/test_plugin_surface.py::test_no_console_log_in_plugin_production_code` enforces the `client.app.log` migration on every plugin.

## Future work

- When OpenCode upstream merges PR `sst/opencode#24293` (broader parent-permission inheritance), this ADR should be revisited to assess whether Layer 2 can be slimmed down. Until then, both layers stay.
