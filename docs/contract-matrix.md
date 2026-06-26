# rldyour Adapter Contract Matrix

`references/rldyour-contract.json` is the machine-readable source of truth for
canonical rldyour workflow IDs in this OpenCode adapter. Validate it with:

```bash
python3 scripts/validate_contract.py
```

## Adapter

| Field | Value |
|---|---|
| Adapter | `opencode` |
| Contract version | `1.0.0` |
| Updated | `2026-05-21` |

## Domains

`browser`, `config`, `design`, `docs-sync`, `explore`, `flow`, `lsp`,
`rules`, `security`, `serena`.

## Manual Sync Flow

| Canonical ID | OpenCode surface | Cross-tool parity |
|---|---|---|
| `flow.sync.manual` | `/ry-sync` command | Canonical manual sync flow. Claude maps it to `/ry-sync`; Codex maps it to the `ry-sync` skill/prompt surface. |
| `flow.repair` | `/ry-repair` command + `ry-repair` skill | Canonical repository-repair flow. Claude maps it to `/rldyour-flow:ry-repair`; Codex maps it to `$rldyour-flow:ry-repair`. |

## OpenCode-Only Surfaces

| Canonical ID | OpenCode surface | Reason |
|---|---|---|
| `agent.adapter.opencode-customizer` | `@customize-opencode` | OpenCode-specific config/plugin/schema editor. |

## Security Posture

OpenCode publishes owner-standard full-auto primary permissions by default.
Top-level, `build`, and `plan` contexts use `edit: "allow"` and
`bash: "allow"`. The aliases `yolo`, `full-auto`, and
`dangerously-skip-permissions` refer to this standard posture.

`permission.ask` remains intentionally absent from the enforcement boundary.
Dynamic blocking of high-impact shell patterns stays in `tool.execute.before`
through `ry-shell-strategy`.

## Agent Roles

| Canonical ID | OpenCode agent |
|---|---|
| `agent.explore.research` | `ry-explore` |
| `agent.review.architecture` | `flow-architecture-review` |
| `agent.review.consistency` | `flow-consistency-review` |
| `agent.review.integration` | `flow-integration-review` |
| `agent.review.quality` | `flow-quality-review` |
| `agent.review.security` | `flow-security-review` |
| `agent.review.verification` | `flow-verification-review` |
| `agent.sync.serena-memory` | `flow-memory-sync` |

## Lifecycle Hooks

| Canonical ID | Plugin | Hook | Class |
|---|---|---|---|
| `session.start.context` | `ry-bootstrap` | `event` (`session.created`) | lifecycle |
| `session.compaction.context` | `ry-bootstrap` | `experimental.session.compacting` | lifecycle |
| `session.compaction.autocontinue` | `ry-bootstrap` | `experimental.compaction.autocontinue` | lifecycle |
| `prompt.system.runtime-context` | `ry-system-context` | `experimental.chat.system.transform` | context |
| `tool.pre.env-protection` | `ry-env-protection` | `tool.execute.before` | guardrail |
| `tool.pre.git-policy` | `ry-shell-strategy` | `tool.execute.before` | guardrail |
| `shell.env.noninteractive` | `ry-shell-strategy` | `shell.env` | guardrail |
| `tool.post.commit-advice` | `ry-flow-hooks` | `tool.execute.after` | advisory |
| `command.pre.audit` | `ry-command-audit` | `command.execute.before` | observability |
| `permission.event.audit` | `ry-permission-events` | `event` (`permission.asked` / `permission.replied`) | observability |
| `tool.definition.routing-hints` | `ry-tool-hints` | `tool.definition` | routing |
| `tool.custom.diagnostics` | `ry-tools` | `tool` | tool-registration |
| `session.idle.sync-reminder` | `ry-sync-reminder` | `event` (`session.idle`) | advisory |

`permission.ask` is intentionally absent. Source/runtime inspection originally
proved this on OpenCode v1.15.4 and the current v1.17.11 baseline keeps the
same repository policy: enforcement uses static permission config plus
runtime-proven `tool.execute.before` guards, not `permission.ask`.
