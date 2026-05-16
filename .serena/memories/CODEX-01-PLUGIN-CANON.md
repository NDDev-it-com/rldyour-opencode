<!-- Memory Metadata
Last updated: 2026-05-17
Last commit: 45e5539 chore(serena): sync project knowledge after cda4c1d
Scope: opencode.json, .opencode/agents/, .opencode/commands/, .opencode/skills/, .opencode/plugins/, references/opencode-plugin-patterns.md, references/reviewer-protocol.md, AGENTS.md
Area: CODEX
-->

# CODEX-01-PLUGIN-CANON

## Purpose

Canonical facts for the OpenCode marketplace runtime: config model inheritance, MCP tool naming, plugins, agents, commands, skills, and domain boundaries.

## Source Of Truth

- `opencode.json`: model selection, permissions, primary agents, MCP servers, LSP servers, compaction, watcher, plugin list.
- `.opencode/plugins/*.ts`: 10 OpenCode server-side plugin hook implementations.
- `.opencode/agents/*.md`: 9 subagent definitions.
- `.opencode/commands/*.md`: 10 slash commands.
- `.opencode/skills/*/SKILL.md`: 32 on-demand skill definitions.
- `references/opencode-plugin-patterns.md`: hook-surface and tool-ID reference.
- `references/reviewer-protocol.md`: reviewer subagent runtime protocol.
- `AGENTS.md`: domain ownership and tool-priority policy.

## Entry Points

- `opencode.json.model`: `opencode-go/glm-5.1`.
- `opencode.json.small_model`: `opencode-go/glm-5.1`.
- `opencode.json.default_agent`: `build`.
- `opencode.json.agent`: only primary/built-in agent settings; subagents live in `.opencode/agents/`.
- `.opencode/plugins/ry-tool-hints.ts`: appends MCP routing hints using OpenCode's runtime tool ID format.

## Current Behavior

- No agent frontmatter or `opencode.json.agent.*` block has a hardcoded model override at HEAD. All primary, hidden built-in, reviewer, memory-sync, explore, and customize agents inherit top-level `model`.
- The 9 subagents are: `customize-opencode`, `flow-architecture-review`, `flow-consistency-review`, `flow-integration-review`, `flow-memory-sync`, `flow-quality-review`, `flow-security-review`, `flow-verification-review`, and `ry-explore`.
- Reviewer subagents are hidden, use `edit: deny`, and keep git-read bash allowlists. `flow-security-review` has `steps: 42`; other reviewer tracks use `steps: 36`.
- `flow-memory-sync` is the only review-track subagent with `edit: allow`; it is scoped to `.serena/memories/` work and denies `task` and `external_directory`.
- `ry-explore` inherits the top-level model, has `steps: 90`, and denies edit/task/external directory access.
- `customize-opencode` inherits the top-level model and keeps `steps: 36`, `temperature: 0.1`, and `color: accent`.
- The 10 local plugins remain auto-discovered from `.opencode/plugins/`: `ry-bootstrap.ts`, `ry-command-audit.ts`, `ry-env-protection.ts`, `ry-flow-hooks.ts`, `ry-permission-policy.ts`, `ry-shell-strategy.ts`, `ry-sync-reminder.ts`, `ry-system-context.ts`, `ry-tool-hints.ts`, `ry-tools.ts`.
- `opencode.json` declares 13 MCP servers: `serena`, `sequential-thinking`, `playwright`, `chrome-devtools`, `context7`, `deepwiki`, `grep`, `semgrep`, `shadcn`, `dart-flutter`, `figma`, `github`, `openai-docs`.
- `opencode.json` declares 8 custom LSP servers: `ruff`, `vscode-html`, `vscode-css`, `vscode-json`, `docker`, `taplo`, `marksman`, `qmlls`.

## Contracts And Data

- OpenCode v1.14.48 MCP tool names use `<server>_<tool>` with one underscore after the sanitized server name; dashes inside server/tool names are preserved. Examples in current files include `serena_find_symbol`, `context7_resolve-library-id`, `figma_*`, `playwright_*`, `chrome-devtools_*`, `shadcn_*`, `deepwiki_*`, and `grep_*`.
- Claude Code-style `mcp__<server>__<tool>` names do not match OpenCode runtime tool IDs and must not be used in active agents, skills, commands, or plugin hints.
- Historical ADR files may still contain old `mcp__` examples inside preserved historical text, but each ADR starts with a supersession banner that points to current config facts.
- Skills require frontmatter `name` and `description`; forbidden OpenCode skill frontmatter includes `allowed-tools`, `disable-model-invocation`, `model`, `effort`, `maxTurns`, `paths`, `context`, and `agent`.
- Agent `color` values must be hex (`#rrggbb`) or one of `primary`, `secondary`, `accent`, `success`, `warning`, `error`, `info`.

## Invariants

- `opencode.json` is the only runtime config authority for top-level `model` and `small_model`.
- Do not reintroduce per-agent model overrides unless the user intentionally changes the inheritance policy.
- Do not reintroduce `mcp__` tool names into active routing instructions.
- Keep plugin hook facts aligned with `@opencode-ai/plugin` runtime types and `references/opencode-plugin-patterns.md`.

## Change Rules

- When changing model policy, update `opencode.json`, `.opencode/agents/*.md`, `references/reviewer-protocol.md`, `AGENTS.md`, ADR supersession banners if relevant, and these memories together.
- When changing MCP names or servers, update `opencode.json`, `AGENTS.md`, affected skills/commands/agents, plugin hints, and tests that blacklist legacy aliases.
- When adding an agent, skill, command, or plugin, update the relevant count and domain table in `AGENTS.md` and add or adjust validation tests if the shape changes.

## Verification

- `python3 - <<'PY' ... json.load(open("opencode.json")) ...`: verifies model inheritance, MCP count, LSP count, and agent keys.
- `rg -n 'mcp__|anthropic/claude|opencode-go/glm|serena_|context7_|figma_|playwright_|chrome-devtools_|shadcn_' .opencode/agents .opencode/commands .opencode/skills references docs/decisions AGENTS.md opencode.json`: verifies current and historical tool/model references.
- `bash scripts/validate_config.sh`: validates config/frontmatter contracts.
- `python3 -m pytest scripts/tests/test_plugin_surface.py scripts/tests/test_opencode_resolve.py scripts/tests/test_skill_routing.py`: targeted checks for plugin surface, OpenCode resolution, and skill routing.
