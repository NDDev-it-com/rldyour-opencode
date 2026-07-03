# Claude Code Project Memory - rldyour-opencode

This is the OpenCode-native project memory for `rldyour-opencode`.
It is the canonical runtime overlay for OpenCode surfaces in this repository.

## Source of Truth

- `opencode.json`
- `.opencode/**`
- `references/opencode-baseline.json`
- `scripts/*.sh`
- `scripts/*.py`
- `references/opencode-baseline.json`

## Runtime Baseline

- OpenCode runtime and SDK pins are declared in:
  - `references/opencode-baseline.json`
  - `opencode.json`
  - `/.opencode/plugins`
- Installer/runtime checks should confirm the same pinned commit and runtime floor each time.

## Boundaries

Use OpenCode-native surfaces only:

- `opencode.json`
- `.opencode/agents/*.md`
- `.opencode/commands/*.md`
- `.opencode/plugins/*.ts`
- `.opencode/skills/*/SKILL.md`
- `references/`

Do not introduce Claude/Antigravity/Codex/Gemini native formats as runtime surfaces.

## Installer and Local Checks

```bash
bash scripts/install_system_opencode.sh --dry-run
bash scripts/install_system_opencode.sh --apply
bash scripts/doctor_opencode.sh
```

Repository validations:

```bash
python3 scripts/validate_config.sh
python3 scripts/validate_contract.py
python3 scripts/validate_opencode_schema.py
python3 scripts/validate_opencode_baseline.py
python3 scripts/check_baseline_consistency.py
python3 scripts/validate_instruction_docs.py
```

Browser/provider policy remains aligned globally:
Webwright for long-horizon tasks, Playwright CLI for UI/asset evidence, and Chrome
DevTools MCP for console/network/performance.

## Task Policy

- Preserve OpenCode command/agent/plugin namespaces; do not cross-wire to non-OpenCode
  command surfaces.
- Prefer explicit `--apply`/`--safe-mode` paths for installer changes.
- Do not commit secrets, browser artifacts, or local runtime markers.
- Keep repository context files and `.serena/` memories aligned with pinned contracts.

## Where canonical project knowledge lives

- `AGENTS.md` is the tracked install/CI truth source.
- `.serena/project.yml` and `.serena/memories/` contain durable context.
- runtime baseline is authoritative in `references/opencode-baseline.json` and `opencode.json`.

## What Claude Code should NOT do

- Do not edit `.claude/CLAUDE.md` for OpenCode-specific content outside this module.
- Do not apply Codex or Antigravity native runtime artifacts in this adapter.

## Validation Claude Code MUST run before delivery

```bash
python3 scripts/validate_instruction_docs.py
python3 scripts/validate_contract.py
python3 scripts/validate_opencode_baseline.py
```
