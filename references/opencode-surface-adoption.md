# OpenCode Surface Adoption

Verified: 2026-05-29

Source of truth:
- Runtime baseline: `references/opencode-baseline.json`
- Vendored schema: `references/opencode-config.schema.v1.15.12.json`
- Official docs and changelog: `https://opencode.ai/docs/` and `https://opencode.ai/changelog`

## Decisions

| Surface | Introduced | Decision | Implementation | Validator |
| --- | --- | --- | --- | --- |
| OpenCode runtime/schema/package baseline | 1.15.12 | Adopted | `opencode-ai`, `@opencode-ai/plugin`, `@opencode-ai/sdk`, and the vendored config schema are pinned to `1.15.12`; no config migration was required. | `scripts/check_baseline_consistency.py`; `scripts/validate_opencode_schema.py` |
| `acp-next` prompt, slash command, and usage update forwarding | 1.15.12 | Operational | Runtime capability only; adapter command and skill declarations stay native OpenCode files. | installed-runtime smoke |
| OpenAI responses WebSocket transport | 1.15.12 | Future | Optional runtime flag `OPENCODE_EXPERIMENTAL_WEBSOCKETS=true`; no owner-default config change. | installed-runtime smoke |
| Adaptive reasoning controls for Anthropic Opus 4.7+ | 1.15.12 | Operational | Runtime behavior only; the adapter does not add Claude Code model syntax to OpenCode config. | `scripts/validate_contract.py` |
| `headerTimeout` provider config | 1.15.11 | Future | No provider-specific timeout is currently needed; keep schema support through vendored config schema. | `scripts/validate_opencode_schema.py` |
| Background agents push updates without polling | 1.15.11 | Operational | Runtime behavior only; no config migration required. | installed-runtime smoke |
| Partial `modalities.input` / `modalities.output` config | 1.15.11 | Future | No adapter-specific modality restriction is required for owner full-auto mode. | `scripts/validate_opencode_schema.py` |
| Stable project identity for remote-backed projects | 1.15.11 | Operational | No repository config change required. | n/a |
| Dynamic MCP disconnect when removed | 1.15.11 | Operational | MCP definitions remain in `opencode.json`; validation checks profile/server parity. | `scripts/validate_mcp_profiles.py` |
| Plugin `dispose` hook | 1.15.11 | Future | No local plugin currently needs teardown; add validator coverage when adopting it. | `scripts/check_plugin_hooks.py` |
| Current `permission` object model | current docs | Adopted | `opencode.json` uses `permission`, not deprecated `tools`; root `oc` uses `OPENCODE_CONFIG_CONTENT` for owner full-auto. | `scripts/validate_contract.py` |

## Owner Full-Auto Policy

The owner-standard OpenCode mode intentionally allows broad read, edit, bash,
web, LSP, skill, repo, task, and external-directory access. Agents may read env
and other files when necessary. Do not add hidden static deny patterns unless
the owner explicitly changes this policy.

## Validation

```bash
python3 scripts/validate_opencode_schema.py
python3 scripts/check_plugin_hooks.py
python3 scripts/validate_mcp_profiles.py
```
