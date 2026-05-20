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
| Updated | `2026-05-20` |

## Domains

`browser`, `config`, `design`, `docs-sync`, `explore`, `flow`, `lsp`,
`rules`, `security`, `serena`.

## OpenCode-Only Surfaces

| Canonical ID | OpenCode surface | Reason |
|---|---|---|
| `flow.sync.manual` | `/ry-sync` command | OpenCode has slash commands; Codex sync is prompt/skill-driven and Claude sync is hook/command-dependent. |
| `agent.adapter.opencode-customizer` | `@customize-opencode` | OpenCode-specific config/plugin/schema editor. |

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

`permission.ask` is intentionally absent. In OpenCode v1.15.4 it is present in
SDK types but is not triggered by the permission service; enforcement uses
static permission config plus `tool.execute.before`.
