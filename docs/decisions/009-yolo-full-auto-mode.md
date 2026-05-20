# ADR-009: YOLO / full-auto permission profile

- Status: accepted
- Date: 2026-05-18
- Updated: 2026-05-20
- Deciders: @rldyourmnd
- Consulted: external audit (2026-05-17 archive review), Phase 0+1+2 fixes

## Context and Problem Statement

The marketplace is a single-developer, single-trust-domain personal
configuration repo. The owner runs OpenCode locally with full trust in the
LLM's edits because the LLM operates inside the owner's shell on the
owner's machine. Build-time velocity matters more than DLP-grade
sandboxing — the agent should not be paused for an interactive permission
dialog on every `git status` or `bash scripts/validate_config.sh`.

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

We considered that approach and rejected it for the marketplace's actual
threat model. This ADR locks in the YOLO / full-auto profile choice so
future audits don't propose the same change without re-reading the trade-off.

## Decision Drivers

- The owner is the only operator; there is no untrusted contributor surface.
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
- Granular bash rules in `opencode.json` are evaluated last-match-wins
  and produce dialogues every few seconds during real workflow. That
  friction either trains the operator to click-through "allow" reflexively
  (defeating the purpose) or causes them to disable the gate entirely.
- The repository contains no production secrets, no PII, no
  customer data — only configuration, plugins, scripts, and docs.

## Considered Options

1. **Granular bash allowlist + `bash: ask` default.** Reject. The friction
   tax outweighs the marginal security gain in a single-developer trusted
   environment. Trained click-through behavior is worse than a clear
   "trust the operator + guard catastrophic patterns" model.
2. **No plugin guardrails, raw `allow` everywhere.** Reject. The catastrophic
   patterns (force-push, `rm -rf /`, `--no-verify` on product branches) need
   deterministic dynamic blocking even in a YOLO profile.
3. **YOLO `allow` + `tool.execute.before` guardrails (ADR-006).
   Document the trade-off explicitly.** **Selected.**

## Decision Outcome

`opencode.json` keeps the global YOLO profile:

```json
"permission": {
  "edit": "allow",
  "bash": "allow",
  "webfetch": "allow",
  "websearch": "allow",
  "lsp": "allow",
  "skill": "allow",
  "glob": "allow",
  "grep": "allow",
  "read": "allow"
}
```

Plus the per-agent overrides that already exist in `.opencode/agents/*.md`
for reviewer subagents (`edit: "deny"`, restricted `bash`).

The security boundary is **operator trust + plugin guardrails**, not
sandbox-grade DLP. This is documented in:

- AGENTS.md § Engineering Rules (existing policy text).
- AGENTS.md § CI/CD and Git Mutation Gate (added in Phase 1; prevents
  the agent from silently mutating remote state without user opt-in).
- `docs/security/mcp-trust-boundaries.md` (per-MCP trust classes).
- This ADR (the explicit "we know it's broad and we chose it" record).

## Consequences

Positive:

- Zero interactive friction on routine workflow: every `git status`,
  `bash scripts/validate_config.sh`, `uvx pytest`, etc. runs without
  dialogue.
- Operator's mental model stays simple: "the LLM has my shell; I trust
  it like I trust myself; guardrails catch catastrophic mistakes."
- Reviewer subagents keep their `edit: "deny"` profile, so the YOLO
  default does not weaken read-only review workflows.

Negative:

- An LLM that escapes its instructions can run arbitrary shell commands
  before the operator notices. Mitigations: plugin guardrails for the
  named catastrophic patterns, `gitleaks` and `secret-scan.yml` for
  secrets, no production credentials in `.env*` to begin with.
- External auditors will likely flag this profile again. The accepted
  rebuttal is "see ADR-009 — explicit single-developer trust model with
  plugin defense-in-depth; not a sandbox".

## Compliance

- `scripts/tests/test_shell_strategy_regexes.py` locks the plugin guardrail
  behavior.
- `scripts/check_plugin_hooks.py` prevents typed-but-untriggered hook surfaces
  from being reintroduced as security boundaries.
- `scripts/tests/test_plugin_surface.py` enforces the no-`console.log`
  and audit-trail invariants.
- This ADR is referenced from AGENTS.md § Engineering Rules so external
  reviewers find it before re-litigating the permission model.

## Future work

- If the repository ever grows multi-contributor or starts holding
  production credentials, this ADR should be re-opened and Option 1
  (granular allowlist) revisited.
- If OpenCode upstream lands first-class sandboxing (process isolation,
  filesystem container), evaluate switching the global default to that
  sandbox instead of plugin guardrails.
