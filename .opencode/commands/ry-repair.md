---
description: "Нормализовать репозиторий: source-of-truth scan, semantic entropy audit, technical repairs, validators, docs/memory sync. Repair stale AI-tool context and contracts."
agent: build
---

Repair repository contracts and AI-tool context without silently changing business decisions.

1. Detect project type, branch/worktree, submodules, CI surface, and fullrepo/agent-only policy.
2. Read AGENTS.md, .claude/CLAUDE.md, opencode.json, .opencode skills/commands/agents/plugins, Serena memories, and repository contracts.
3. Inspect GitHub issues/PRs/history through MCP or CLI when available, then verify every issue against current code.
4. Detect semantic entropy: stale docs, stale memories, duplicated instructions, unclear source of truth, broken validators, dead config, hook/MCP/LSP drift, missing ADR/CONTEXT/FUTURE facts.
5. Produce a repair plan split into technical fixes and owner-decision items.
6. Ask the owner before changing business logic, functional behavior, security posture, deployment target, data model, or ADR meaning.
7. Apply technical-only repairs using existing project patterns and native OpenCode surfaces.
8. Run validators, tests, schema checks, hook/plugin checks, and docs/memory freshness checks.
9. Finish through /ry-sync when durable artifacts changed.

Reply in Russian unless the owner explicitly requests another language.

Reference: .opencode/skills/ry-repair/SKILL.md, references/rldyour-contract.json
