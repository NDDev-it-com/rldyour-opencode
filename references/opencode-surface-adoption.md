# OpenCode Surface Adoption

Verified: 2026-05-31

Source of truth:
- Runtime baseline: `references/opencode-baseline.json`
- Vendored schema: `references/opencode-config.schema.v1.15.13.json`
- Official docs and changelog: `https://opencode.ai/docs/` and `https://opencode.ai/changelog`

## Decisions

| Surface | Introduced | Decision | Implementation | Validator |
| --- | --- | --- | --- | --- |
| OpenCode runtime/schema/package baseline | 1.15.13 | Adopted | `opencode-ai`, `@opencode-ai/plugin`, `@opencode-ai/sdk`, and the vendored config schema are pinned to `1.15.13`; no config migration was required. | `scripts/check_baseline_consistency.py`; `scripts/validate_opencode_schema.py` |
| Session metadata through API and SDK | 1.15.13 | Future | Runtime/API capability only; no adapter config or local plugin currently persists custom session metadata. | `scripts/check_plugin_hooks.py` |
| Config loads from opened location upward | 1.15.13 | Operational | Matches the existing project-local `opencode.json` model and OpenCode bridge discovery; no migration required. | installed-runtime smoke |
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
| Current `permission` object model | current docs | Adopted | `opencode.json` uses `permission`, not deprecated `tools`; standalone adapter config explicitly sets the canonical owner primary permissions to `allow`, including `external_directory` and `doom_loop`, and root `oc` mirrors that posture through `OPENCODE_CONFIG_CONTENT`. | `scripts/validate_contract.py`; root `scripts/validate_opencode_permission_profiles.py` |

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
