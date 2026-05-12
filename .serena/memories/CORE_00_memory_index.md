# CORE_00 Memory Index

Last commit: f28aadd

## Purpose

Master registry of `.serena/memories/` for rldyour-opencode. Every memory in this index is fact-only, sourced from current repository files at HEAD `f28aadd`.

## Memory Registry

| ID | File | Scope | Description |
| --- | --- | --- | --- |
| CORE_00 | `CORE_00_memory_index.md` | meta | Master registry |
| ARCH_01 | `ARCH_01_repository_shape.md` | architecture | Repo layout, source-of-truth contract |
| CONFIG_02 | `CONFIG_02_opencode_json.md` | config | `opencode.json` master config |
| INVENTORY_03 | `INVENTORY_03_agents.md` | components | All 9 subagents in `.opencode/agents/` |
| INVENTORY_04 | `INVENTORY_04_commands.md` | components | All 10 commands in `.opencode/commands/` |
| INVENTORY_05 | `INVENTORY_05_skills.md` | components | All 32 skills in `.opencode/skills/` |
| INVENTORY_06 | `INVENTORY_06_plugins.md` | components | 5 TS plugins in `.opencode/plugins/` |
| INVENTORY_07 | `INVENTORY_07_scripts.md` | components | 10 bash scripts in `scripts/` |
| INVENTORY_08 | `INVENTORY_08_references.md` | components | 15 reference docs in `references/` |
| INVENTORY_09 | `INVENTORY_09_mcp_servers.md` | integration | 13 MCP servers in `opencode.json` |
| CONTRACT_10 | `CONTRACT_10_fullrepo_and_excludes.md` | contract | Fullrepo branch + `.git/info/exclude` rules |
| CONTRACT_11 | `CONTRACT_11_domain_boundaries.md` | contract | Domain ownership matrix |
| POLICY_12 | `POLICY_12_communication_quality.md` | policy | RU/EN, commits, engineering rules |
| CI_13 | `CI_13_validate_workflow.md` | quality | GitHub Actions validation gate |

## Project facts

- **Repository**: `rldyour-opencode` (path: `/Users/rldyourmnd/Desktop/open_base/rldyour-opencode`).
- **Type**: OpenCode AI coding agent configuration marketplace.
- **Version**: `VERSION` → `0.7.0`. All 7 entries in `CHANGELOG.md` dated 2026-05-12.
- **License**: MIT (`LICENSE`).
- **HEAD**: `f28aadd` — "feat: add missing commands, LSP scripts, flow scripts, and flow hooks plugin".
- **Branch**: `main`. Upstream: not configured (no `origin`). Worktrees: 1.

## Anti-Hallucination Contract

Every memory must trace to a verifiable source: current file content at HEAD `f28aadd`, git history, or explicit user input. No speculation, no chat paraphrasing. Code is the source of truth. Memories must be refreshed when reality diverges.

`ry-init` is read-only for memories; only explicit `serena-memory-sync` invocation or a stale-memory hook may add/update memories.
