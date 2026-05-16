<!-- Memory Metadata
Last updated: 2026-05-17
Last commit: dd149aa chore(opencode): align plugin pin with runtime 1.15.3
Scope: .serena/memories/, AGENTS.md, opencode.json, .opencode/, references/, docs/, scripts/
Area: CORE
-->

# CORE-01-INDEX

## Purpose

Master registry for rldyour-opencode Serena memories. These files are fact-only project knowledge for future AI coding sessions and follow the `AREA-01-SLUG.md` taxonomy.

## Source Of Truth

- `opencode.json`: master OpenCode configuration.
- `AGENTS.md`: cross-tool root instructions and domain/source-of-truth rules.
- `.opencode/agents/*.md`: subagent definitions.
- `.opencode/skills/*/SKILL.md`: on-demand skill definitions.
- `.opencode/commands/*.md`: slash command definitions.
- `.opencode/plugins/*.ts`: OpenCode plugin hook implementations.
- `references/*.md`: durable contracts consumed by skills and agents.
- `docs/*.md` and `docs/decisions/*.md`: operator guides and ADR archive.
- `scripts/` and `scripts/tests/`: local validation, diagnostics, fullrepo, and smoke checks.

## Entry Points

- `python3 /home/rldyourmnd/.codex/plugins/cache/rldyour-codex/rldyour-serena-mcp/local/scripts/serena_memory_state.py`: freshness analyzer used for this sync because the repo-local plugin path is not present.
- `/home/rldyourmnd/.codex/plugins/cache/rldyour-codex/rldyour-serena-mcp/local/scripts/commit_serena_knowledge.sh`: acknowledgement/commit helper to run after memory edits.

## Current Behavior

- Source commit for this sync is `cda4c1d`; current git HEAD during memory rewrite is the knowledge-only commit `45e5539`.
- Newest previously synced commit was `1f1510b`.
- The freshness analyzer reported changed non-knowledge scope across agents, commands, skills, `AGENTS.md`, ADR banners, `opencode.json`, and `references/reviewer-protocol.md`.
- The analyzer taxonomy specifies `CORE-01-INDEX.md` as the index memory and `AREA-01-SLUG.md` as the filename pattern.

## Contracts And Data

| Memory | Area | Owns |
| --- | --- | --- |
| `CORE-01-INDEX.md` | CORE | Memory map, sync evidence, taxonomy |
| `CORE-02-PROJECT-SHAPE.md` | CORE | Repository identity, source-of-truth layout, agent-only/fullrepo boundaries |
| `CODEX-01-PLUGIN-CANON.md` | CODEX | OpenCode config, plugins, MCP/LSP naming, agents, commands, skills |
| `DOCS-01-INSTRUCTIONS.md` | DOCS | `AGENTS.md`, `.claude/CLAUDE.md`, ADR banners, reviewer protocol, docs/references boundary |
| `RELEASE-01-VALIDATION.md` | RELEASE | Validation scripts, test suites, CI, diagnostics and release gates |
| `TECHDEBT-01-NOW.md` | TECHDEBT | Known stale-reference and operational gaps that remain encoded in files |

## Invariants

- Every memory must include `Last commit: 45e5539 ...` until the next sync.
- New or updated memories must use `AREA-01-SLUG.md`; old underscore names are obsolete.
- Memory facts must trace to current code/config/tests at HEAD first, then recent git history or diff.

## Change Rules

- Update this index in the same sync pass as any new, deleted, or renamed memory.
- Do not store runtime snapshots, chat history, secrets, cookies, private keys, or speculative plans in memories.
- Keep memories narrow; split by durable domain ownership rather than appending unrelated facts.

## Verification

- `python3 /home/rldyourmnd/.codex/plugins/cache/rldyour-codex/rldyour-serena-mcp/local/scripts/serena_memory_state.py`: reports memory freshness and analyzer scope.
- `find .serena/memories -maxdepth 1 -type f -name '*.md' -printf '%f\n' | sort`: verifies active memory filenames.
