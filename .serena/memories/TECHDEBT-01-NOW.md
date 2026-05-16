<!-- Memory Metadata
Last updated: 2026-05-17
Last commit: 45e5539 chore(serena): sync project knowledge after cda4c1d
Scope: docs/decisions/, references/rules-policy.md, .serena/memories/
Area: TECHDEBT
-->

# TECHDEBT-01-NOW

## Purpose

Current verified gaps and anti-regression notes that future sessions should not confuse with active runtime behavior.

## Source Of Truth

- `docs/decisions/*.md`: historical ADR archive with supersession banners.
- `references/rules-policy.md`: rule reference that still contains one legacy Sequential Thinking MCP tool-name example.
- `.serena/memories/`: current memory taxonomy and stale old-name cleanup.

## Current Behavior

- The active OpenCode runtime uses `<server>_<tool>` MCP tool IDs, but preserved historical ADR bodies still contain legacy `mcp__...` examples below their supersession banners.
- `references/rules-policy.md` still contains `mcp__sequential-thinking__*` in a rule example. This is a verified stale reference outside the changed-file list for this sync.
- Old underscore memory filenames (`CORE_00_memory_index.md`, `CORE_01_project_shape.md`, `CORE_02_opencode_config.md`, `CORE_03_plugins_agents_commands.md`, `CORE_04_skills_references_scripts.md`, `CONTRACT_10_fullrepo_and_excludes.md`, `POLICY_12_communication_quality.md`, `DOCS_14_marketplace_operations.md`) were replaced by the `AREA-01-SLUG.md` taxonomy during this sync.

## Contracts And Data

- Active agents, commands, and skills should use OpenCode v1.14.48 MCP tool IDs such as `serena_find_symbol`, `context7_resolve-library-id`, `figma_*`, `playwright_*`, and `chrome-devtools_*`.
- Historical ADR examples may remain when the supersession banner clearly marks them historical.
- Known stale reference docs should be corrected in a normal docs cleanup task, not silently treated as runtime truth.

## Invariants

- Do not cite preserved ADR code examples as current runtime behavior without reading the supersession banner.
- Do not reintroduce old underscore memory filenames for updated memories.
- Do not treat `mcp__` hits as automatically wrong; first classify whether the hit is active instructions or preserved historical context.

## Change Rules

- When cleaning stale `mcp__` references, prioritize active `references/*.md`, `.opencode/agents`, `.opencode/skills`, `.opencode/commands`, and `AGENTS.md`.
- If ADR historical text is edited, preserve the archival intent or create a new ADR instead of rewriting history without a banner.

## Verification

- `rg -n 'mcp__|anthropic/claude|opencode-go/glm' .opencode/agents .opencode/commands .opencode/skills references docs/decisions AGENTS.md opencode.json`: classifies active vs historical stale references.
- `find .serena/memories -maxdepth 1 -type f -name '*.md' -printf '%f\n' | sort`: verifies memory taxonomy.
