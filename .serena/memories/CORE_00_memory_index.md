# CORE_00 Memory Index

Last commit: 22fb8ab

## Purpose

Master registry of `.serena/memories/` for rldyour-opencode. Every memory in this index is fact-only, sourced from current repository files at HEAD `f28aadd`. Anti-hallucination contract applies to all entries.

## Memory Registry

| ID | File | Scope | Description |
| --- | --- | --- | --- |
| CORE_00 | `CORE_00_memory_index.md` | meta | Master registry |
| CORE_01 | `CORE_01_project_shape.md` | architecture | Repo topology, layout, source-of-truth contract, communication policy |
| CORE_02 | `CORE_02_opencode_config.md` | config | `opencode.json` master config + MCP (13) + LSP (8 custom) + permissions |
| CORE_03 | `CORE_03_plugins_agents_commands.md` | components | 5 plugins + 9 agents + 10 commands + domain boundaries |
| CORE_04 | `CORE_04_skills_references_scripts.md` | components | 32 skills + 15 references + 11 scripts + CI gate + docs/ |
| CONTRACT_10 | `CONTRACT_10_fullrepo_and_excludes.md` | contract | Fullrepo orphan branch + `.git/info/exclude` workflow detail |
| POLICY_12 | `POLICY_12_communication_quality.md` | policy | RU/EN, Conventional Commits, engineering rules, /ry-sync gate, 10 Don'ts |
| DOCS_14 | `DOCS_14_marketplace_operations.md` | operations | `docs/` marketplace guides (release / dependency / rollback) |

## Project facts

- **Repository**: `rldyour-opencode` (path: `/Users/rldyourmnd/Desktop/open_base/rldyour-opencode`).
- **Type**: OpenCode AI coding agent configuration marketplace.
- **Version**: `VERSION` → `0.7.0`. All 7 entries in `CHANGELOG.md` dated `2026-05-12`.
- **License**: MIT (`LICENSE`).
- **HEAD**: `22fb8ab` — "chore(release): 0.8.0".
- **VERSION**: `0.8.0` (bumped from 0.7.0; CHANGELOG.md has full 0.8.0 entry dated 2026-05-13).
- **Validated against**: `opencode v1.14.48` (`opencode debug config` resolves cleanly; `bash scripts/validate_config.sh` exits 0; `opencode debug agent <name>` passes for all 9 agents).
- **Sync commits (Serena)**: `41950f5`, `a5bd8cf`, `9d954db`, `c4d8d9c`, `ca6f518`, plus subsequent edits after `22fb8ab`.
- **Last ry-start lifecycle (0.8.0)**: commits `a5d50f8` (validator rewrite), `37d6861` (AGENTS.md skill+plugin events), `f961349` (README catalog refresh), `05e5a75` (ry-bootstrap dynamic MCP), `104a13d` (docs/ marketplace guides), `3c442a4` (customize-opencode body fix), `f79c24b` (SSoT command-block gate + YAML block-scalar + utf-8-sig), `c13c87e` (plugin dedup + Bun.file warn), `b89663e` (CI delegates to validate_config.sh), `5b6261c` (script log helpers), `3a91183` (AGENTS.md color spec + docs SoT + package.json honesty), `22fb8ab` (release 0.8.0).
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
