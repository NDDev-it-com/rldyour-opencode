---
description: "Нормализовать репозиторий: source-of-truth scan, semantic entropy audit, technical repairs, validators, docs/memory sync. Repair stale AI-tool context and contracts."
agent: build
---

Repair repository contracts and AI-tool context without silently changing business decisions.

1. Detect project type, branch/worktree, submodules, CI surface, and fullrepo/agent-only policy.
2. Read AGENTS.md, .claude/CLAUDE.md, opencode.json, .opencode skills/commands/agents/plugins, Serena memories, and repository contracts.
3. Inspect GitHub issues/PRs/history through MCP or CLI when available, then verify every issue against current code.
4. When the root control plane is present, use `scripts/ry_repair_sync.py --plan/--check` before claiming local repo, system AI CLI config, Serena, GitHub, or fullrepo sync.
5. Enforce retired-tool cleanup through positive active inventories and the generic retired-tool residue validator. Do not add new tool-specific `validate_no_<tool>.py` checks; historical changelog entries may remain only when explicitly historical.
6. Detect semantic entropy: stale docs, stale memories, duplicated instructions, unclear source of truth, broken validators, dead config, hook/MCP/LSP drift, missing ADR/CONTEXT/FUTURE facts.
7. Produce a repair plan split into technical fixes and owner-decision items.
8. Ask the owner before changing business logic, functional behavior, security posture, deployment target, data model, or ADR meaning.
9. Apply technical-only repairs using existing project patterns and native OpenCode surfaces.
10. Run validators, tests, schema checks, hook/plugin checks, installed-config checks, and docs/memory freshness checks.
11. Finish through /ry-sync when durable artifacts changed.

Reply in Russian unless the owner explicitly requests another language.

Reference: .opencode/skills/ry-repair/SKILL.md, references/rldyour-contract.json
