# CORE_00 Memory Index

Last commit: 3c434ae

## Purpose

Master registry of `.serena/memories/` for rldyour-opencode. Every memory in this index is fact-only, sourced from current repository files at HEAD `f28aadd`. Anti-hallucination contract applies to all entries.

## Memory Registry

| ID | File | Scope | Description |
| --- | --- | --- | --- |
| CORE_00 | `CORE_00_memory_index.md` | meta | Master registry |
| CORE_01 | `CORE_01_project_shape.md` | architecture | Repo topology, layout, source-of-truth contract, communication policy |
| CORE_02 | `CORE_02_opencode_config.md` | config | `opencode.json` master config + MCP (13) + LSP (8 custom) + permissions |
| CORE_03 | `CORE_03_plugins_agents_commands.md` | components | 5 plugins + 9 agents + 10 commands + domain boundaries |
| CORE_04 | `CORE_04_skills_references_scripts.md` | components | 32 skills + 15 references + 10 scripts + CI gate |
| CONTRACT_10 | `CONTRACT_10_fullrepo_and_excludes.md` | contract | Fullrepo orphan branch + `.git/info/exclude` workflow detail |
| POLICY_12 | `POLICY_12_communication_quality.md` | policy | RU/EN, Conventional Commits, engineering rules, /ry-sync gate, 10 Don'ts |

## Project facts

- **Repository**: `rldyour-opencode` (path: `/Users/rldyourmnd/Desktop/open_base/rldyour-opencode`).
- **Type**: OpenCode AI coding agent configuration marketplace.
- **Version**: `VERSION` → `0.7.0`. All 7 entries in `CHANGELOG.md` dated `2026-05-12`.
- **License**: MIT (`LICENSE`).
- **HEAD**: `3c434ae` — "fix(agents): use schema-valid color values for OpenCode v1.14".
- **Validated against**: `opencode v1.14.48` (`opencode debug config` resolves cleanly).
- **Sync commits (Serena)**: `41950f5`, `a5bd8cf`, `9d954db`, plus subsequent edits after `3c434ae`.
- **Branch**: `main`. Upstream: not configured (no `origin`). Worktrees: 1.

## Anti-Hallucination Contract

Every memory must trace to a verifiable source: current file content at HEAD `f28aadd`, git history, or explicit user input. No speculation, no chat paraphrasing. Code is the source of truth. Memories must be refreshed when reality diverges.

`ry-init` is read-only for memories. Only explicit `serena-memory-sync` invocation or a stale-memory hook may add/update memories.

## Read order for full project mental model

1. CORE_01 — repository shape and source-of-truth contract.
2. CORE_02 — opencode.json master configuration.
3. CORE_03 — plugins, agents, commands, domain boundaries.
4. CORE_04 — skills, references, scripts, CI.
5. CONTRACT_10 — fullrepo sync workflow (deep).
6. POLICY_12 — communication and quality rules (deep).
