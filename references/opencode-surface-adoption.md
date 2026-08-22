# OpenCode Surface Adoption

Verified: 2026-07-10

Source of truth:
- Runtime baseline: `references/opencode-baseline.json`
- Vendored schema: `references/opencode-config.schema.v1.17.18.json`
- Official docs and release notes: `https://opencode.ai/docs/config` and `https://github.com/anomalyco/opencode/releases/tag/v1.17.18`

## Current adopted surface: 1.17.18

| Surface | Introduced | Decision | Implementation | Validator |
| --- | --- | --- | --- | --- |
| OpenCode runtime/schema/package baseline | runtime/schema 1.17.18; plugin/SDK 1.18.5 | Adopted | `opencode-ai` and the vendored config schema remain pinned to the behaviorally verified `1.17.18`; `@opencode-ai/plugin` and `@opencode-ai/sdk` move together at `1.18.5`. npm package metadata is the authoritative package channel, GitHub Releases are informational, and the vendored schema remains `references/opencode-config.schema.v1.17.18.json`. | `scripts/check_baseline_consistency.py`; `scripts/validate_opencode_schema.py` |
| Top-level `references` config key | 1.17.0-1.17.18 | Future | The schema adds `references` ("Named git or local directory references", git/local sub-types); 1.17.1 adds per-reference usage descriptions and `@`-autocomplete hiding, and the unchanged 1.17.18 schema keeps the surface current. The adapter does not currently need named reference entries; adopt when an owner workflow requires shared reference directories. | `scripts/validate_opencode_schema.py` |
| `fff`-backed file search and `X-Session-Id` proxy headers | 1.17.0 | Operational | Faster project file search and sticky-routing session headers are runtime behavior; no config migration is required. | installed-runtime smoke |
| MCP reliability fixes and remote config auth recovery | 1.17.0-1.17.18 | Adopted | MCP tool calls receive abort signals, catalogs paginate (1.17.14 fixes paginated catalogs losing tool metadata and output schema validation), servers respect advertised capabilities and configured timeouts for prompt/resource requests, client-setup failures fail cleanly, and 1.17.2 recovers from expired remote config auth by prompting login. Treat as runtime correctness; `opencode.json` MCP definitions stay unchanged. | `scripts/validate_mcp_profiles.py`; `scripts/smoke_mcp_capabilities.py` |
| Claude Fable reasoning support | 1.17.0-1.17.18 | Operational | Runtime adds Claude Fable reasoning handling and fixes Anthropic fallback responses; provider/model selection stays owner policy in `opencode.json`. | installed-runtime smoke |
| Code mode MCP adapter | 1.17.14 | Future | 1.17.14 adds a code mode MCP adapter for confined orchestration scripts against connected MCP tools and hides the `execute` tool unless code mode is enabled. No `opencode.json` surface is adopted; evaluate when an owner workflow needs script-driven MCP orchestration. | release notes `v1.17.14`; `scripts/validate_opencode_schema.py` |
| Copilot zero-batch pricing guard and Meta Muse Spark prompt | 1.17.18 | Adopted | Runtime prevents crashes and invalid pricing when GitHub Copilot reports a zero billing batch size and supplies the model-specific system prompt for Meta Muse Spark. These are runtime/provider correctness improvements; no adapter config migration is required. | release notes `v1.17.18`; installed-runtime smoke |
| Subagent permission restoration | 1.17.2 | Adopted | Runtime lets subagents use their configured permissions again. This preserves the adapter's explicit primary/subagent permission profiles; it does not weaken reviewer subagent read-only policy. | `scripts/validate_config.sh`; root `scripts/validate_opencode_permission_profiles.py` |
| TUI footer/status-line content customization | not available in 1.17.18 stable config | Future | The stable `opencode.json`/`tui.json` surface still exposes no footer or status-line content keys in `1.17.18`. The experimental `@opencode-ai/plugin` TUI slot API (`app_bottom`, `home_footer`, `sidebar_footer` slots) has existed unchanged since `1.16.2` and remains experimental; the built-in session footer is not plugin-customizable through it. The owner status-line requirement stays covered by Claude Code `statusLine` and Codex `[tui].status_line`; adopt here when a stable surface lands. | `scripts/validate_opencode_schema.py`; installed-runtime smoke |

## Historical baseline notes: 1.17.14

| Surface | Introduced | Decision | Implementation | Validator |
| --- | --- | --- | --- | --- |
| OpenCode runtime/schema/package baseline | 1.17.14 | Adopted | Historical package/schema baseline superseded by the current `1.17.18` row. The `v1.17.14` config schema snapshot is byte-identical to the current `v1.17.18` snapshot (SHA-256 `57c02429`). | `scripts/check_baseline_consistency.py`; `scripts/validate_opencode_schema.py` |

## Historical baseline notes: 1.17.13

| Surface | Introduced | Decision | Implementation | Validator |
| --- | --- | --- | --- | --- |
| OpenCode runtime/schema/package baseline | 1.17.13 | Adopted | Historical package/schema baseline superseded by the current `1.17.18` row. The `v1.17.13` config schema snapshot is byte-identical to the current `v1.17.18` snapshot (SHA-256 `57c02429`). | `scripts/check_baseline_consistency.py`; `scripts/validate_opencode_schema.py` |

## Historical baseline notes: 1.17.7

| Surface | Introduced | Decision | Implementation | Validator |
| --- | --- | --- | --- | --- |
| OpenCode runtime/schema/package baseline | 1.17.7 | Adopted | Historical package/schema baseline superseded by the current `1.17.18` row. The `v1.17.7` config schema snapshot is byte-identical to the `v1.17.13`, `v1.17.14`, and current `v1.17.18` snapshots (SHA-256 `57c02429`). | `scripts/check_baseline_consistency.py`; `scripts/validate_opencode_schema.py` |

## Historical baseline notes: 1.17.1

| Surface | Introduced | Decision | Implementation | Validator |
| --- | --- | --- | --- | --- |
| OpenCode runtime/schema/package baseline | 1.17.1 | Adopted | Historical package/schema baseline superseded by the current `1.17.18` row. | `scripts/check_baseline_consistency.py`; `scripts/validate_opencode_schema.py` |

## Historical baseline notes: 1.16.2

| Surface | Introduced | Decision | Implementation | Validator |
| --- | --- | --- | --- | --- |
| OpenCode runtime/schema/package baseline | 1.16.2 | Adopted | `opencode-ai`, `@opencode-ai/plugin`, `@opencode-ai/sdk`, and the vendored config schema are pinned to `1.16.2`; the schema content is byte-identical to the previously vendored `v1.16.0` snapshot, but the filename tracks the current runtime baseline. | `scripts/check_baseline_consistency.py`; `scripts/validate_opencode_schema.py` |
| Provider-compatible reasoning summaries | 1.16.2 | Adopted | Reasoning summaries are runtime-gated by provider capability. Do not assume GPT-5 or OpenAI-compatible providers support every summary mode, and do not add speculative provider overrides. | installed-runtime smoke; `scripts/validate_config.sh` |
| Refuse loose edit matches | 1.16.2 | Adopted | Treat this as runtime safety. Adapter plugins and docs should still produce exact edit/search context; no config migration is required. | installed-runtime smoke |
| Backgroundable running subagents | 1.16.2 | Operational | Running subagents can be sent to the background. Repository truth remains docs/config/Serena; background sessions are runtime state, not committed project state. | installed-runtime smoke |
| Session system-context persistence | 1.16.2 | Operational | Runtime sessions persist system context updates during long conversations, but durable project truth remains `opencode.json`, docs, and Serena memories. | installed-runtime smoke |
| Snowflake Cortex provider support | 1.16.2 | Future | Optional provider capability only. Do not commit Snowflake credentials or switch the owner-default provider without explicit owner policy. | `scripts/validate_opencode_schema.py` |
| Permission replies use the correct session directory | 1.16.2 | Adopted | Aligns with project-local config resolution. Continue validating the opened target with `opencode debug config`. | installed-runtime smoke |
| Dedicated TUI config and provider options | current docs | Adopted | Keep active `opencode.json` free of legacy top-level `theme`, `keybinds`, and `tui` keys; TUI state belongs in dedicated `tui.json` / `OPENCODE_TUI_CONFIG`. Provider options such as `timeout`, `chunkTimeout`, and `setCacheKey` are explicit only when owner policy requires them. | `scripts/validate_config.sh`; `scripts/validate_opencode_schema.py` |
| Managed workspace cloning with dirty/untracked preservation | 1.16.0 | Operational | Runtime behavior only; keep repository git policy in rldyour-flow and validate workspace state with git status before release operations. | installed-runtime smoke |
| Move sessions between workspaces/directories | 1.16.0 | Future | Runtime/session capability only; do not persist adapter assumptions until a first-party command or plugin needs to move sessions. | installed-runtime smoke |
| OpenAI model support through AWS Bedrock | 1.16.0 | Future | Provider capability only; owner-local config keeps current model/provider policy and does not add Bedrock credentials or provider overrides. | `scripts/validate_opencode_schema.py` |
| Skill discovery and file-based agent loading | 1.16.0 | Adopted | Plural `.opencode/skills/` and `.opencode/agents/` directories remain the native source. Generated `index.json` files stay compatibility metadata, not runtime discovery truth. | `scripts/generate_skills_index.py --check`; `scripts/validate_config.sh` |
| `run --replay` interactive session replay | 1.16.0 | Operational | Add to installed-runtime smoke only; no repository config field is required. | installed-runtime smoke |
| Startup and cancellation reliability fixes | 1.16.0 | Adopted | Treat shell cancellation, delegated-task reasoning variant, OpenAI websocket idle, Windows path normalization, wide-character paste, and ACP cancellation fixes as runtime correctness. No config migration is required. | `scripts/check_baseline_consistency.py` |
| Current `permission` object model | current docs | Adopted | `opencode.json` uses `permission`, not deprecated `tools`; standalone adapter config explicitly sets the canonical owner primary permissions to `allow`, including `external_directory` and `doom_loop`, and root `oc` mirrors that posture through `OPENCODE_CONFIG_CONTENT`. | `scripts/validate_contract.py`; root `scripts/validate_opencode_permission_profiles.py` |
| TUI status line / footer content customization | not available in 1.16.2 stable config | Future | Historical decision, corrected: the stable `opencode.json`/`tui.json` surface exposed no footer/status-line content keys, while the experimental `@opencode-ai/plugin` TUI slot API already carried `app_bottom`, `home_footer`, and `sidebar_footer` slots in `1.16.2`; the built-in session footer was never plugin-customizable. The owner status-line requirement is covered by Claude Code `statusLine` and Codex `[tui].status_line`. | superseded by the 1.17.7 row above |

## Historical baseline notes: 1.15.13 and earlier

Historical rows remain only as evidence for why current policy exists. They are not the active runtime baseline; `references/opencode-baseline.json` and the current adopted surface above define the active baseline.

| Surface | Introduced | Decision | Implementation | Validator |
| --- | --- | --- | --- | --- |
| Session metadata through API and SDK | 1.15.13 | Future | Runtime/API capability only; no adapter config or local plugin currently persists custom session metadata. | `scripts/check_plugin_hooks.py` |
| Config loads from opened location upward | 1.15.13 | Operational | Matches the existing project-local `opencode.json` model and OpenCode bridge discovery; `opencode debug config` remains the installed-runtime resolver smoke from the actual opened target. | installed-runtime smoke |
| Gateway Anthropic adaptive reasoning thinking-block fix | 1.15.13 | Operational | Runtime bugfix only; adapter does not add Claude Code model syntax to OpenCode config. | `scripts/validate_contract.py` |
| Experimental resource policies in config schema | 1.15.13 | Future | Schema support is vendored; owner full-auto remains expressed through stable `permission` keys rather than experimental policy statements. | `scripts/validate_opencode_schema.py` |
| `acp-next` prompt, slash command, and usage update forwarding | 1.15.12 | Operational | Runtime capability only; adapter command and skill declarations stay native OpenCode files. | installed-runtime smoke |
| OpenAI responses WebSocket transport via `OPENCODE_EXPERIMENTAL_WEBSOCKETS=true` | 1.15.12 | Future | Experimental transport flag only; no owner-default config change and no release-safe example enables it. | installed-runtime smoke |
| Adaptive reasoning controls for current Anthropic Opus-class models | 1.15.12 | Operational | Runtime behavior only; the adapter does not add Claude Code model syntax to OpenCode config. | `scripts/validate_contract.py` |
| Custom OpenAI WebSocket base URLs | 1.15.12 | Future | Not applicable until the owner configures a custom OpenAI-compatible WebSocket transport; keep default provider URLs out of repository config. | `scripts/validate_opencode_schema.py` |
| `headerTimeout` provider config | 1.15.11 | Future | No provider-specific timeout is currently needed; keep schema support through vendored config schema. | `scripts/validate_opencode_schema.py` |
| Background agents push updates without polling | 1.15.11 | Operational | Runtime behavior only; no config migration required. | installed-runtime smoke |
| Partial `modalities.input` / `modalities.output` config | 1.15.11 | Future | No adapter-specific modality restriction is required for owner full-auto mode. | `scripts/validate_opencode_schema.py` |
| Stable project identity for remote-backed projects | 1.15.11 | Operational | No repository config change required. | n/a |
| Dynamic MCP disconnect when removed | 1.15.11 | Operational | MCP definitions remain in `opencode.json`; validation checks profile/server parity. | `scripts/validate_mcp_profiles.py` |
| Plugin `dispose` hook | 1.15.11 | Future | No local plugin currently needs teardown; add validator coverage when adopting it. | `scripts/check_plugin_hooks.py` |

## Owner Full-Auto Policy

The standalone adapter intentionally allows read, edit, bash, web, LSP, skill,
task, external-directory, and doom-loop surfaces in the owner primary profile.
The root owner `oc` launcher mirrors that no-prompt posture through
`OPENCODE_CONFIG_CONTENT` for the trusted workstation. Do not add hidden static
deny patterns to the owner profile unless the owner explicitly changes this
policy.

## Validation

```bash
python3 scripts/validate_opencode_schema.py
python3 scripts/check_plugin_hooks.py
python3 scripts/validate_mcp_profiles.py
```
