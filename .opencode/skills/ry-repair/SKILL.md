---
name: ry-repair
description: "Нормализация репозитория: source-of-truth scan, semantic entropy cleanup, stale docs/memory repair, validators, docs/memory sync. Используй для: ry-repair, почини систему, нормализуй репозиторий, убери противоречия. EN triggers: repository repair, semantic entropy cleanup, stale AI-tool context, contract normalization."
---

# ry-repair

## Purpose

Normalize a repository so OpenCode, Codex, and Claude Code can work from the same verified facts with minimal semantic entropy. This is a technical repair flow, not permission to change business logic silently.

For rldyour AI CLI configuration repositories, `/ry-repair` also verifies deterministic install/update/sync convergence through the root `config/ry-repair-sync-contract.json` and `scripts/ry_repair_sync.py` contract when that control plane is present.

## Workflow

1. Detect repository type, branch/worktree, submodules, CI surface, deploy surface, and fullrepo/agent-only policy.
2. Read native instruction/config surfaces: `AGENTS.md`, `.claude/CLAUDE.md`, `opencode.json`, `.opencode/commands`, `.opencode/skills`, `.opencode/agents`, `.opencode/plugins`, and repository contracts.
3. Inspect Serena memories, plans, and research archives for stale facts, unsupported claims, missing taxonomy, duplicated rules, or contradictions with current code.
4. Inspect GitHub issues, pull requests, and recent history through MCP or CLI when available. Verify every issue against current code before treating it as a fact.
5. Inspect MCP/LSP/tooling config, plugin hook lifecycles, commands/skills/agents, CI gates, release manifests, dependency baselines, and docs source-of-truth declarations.
6. When the root control plane is present, run `python3 scripts/ry_repair_sync.py --plan --target "$PWD"` and use `--check` before claiming local repo, system AI CLI config, Serena memory, or GitHub/fullrepo sync.
7. Treat zero-active Semgrep policy as system-wide: installed Claude/Codex/OpenCode configs, active agent/tool surfaces, CI workflows, runtime pins, docs, and release gates must be clean. Keep only negative validators/tests and historical changelog entries.
8. Detect semantic entropy: duplicated docs, stale pins, conflicting instructions, dead config, unclear source-of-truth, missing ADR/CONTEXT/FUTURE facts, broken validators, and adapter parity drift.
9. Produce a repair plan that separates:
   - technical repairs the agent may apply;
   - business, functional, security-posture, deployment-target, data-model, or ADR decisions that require the owner.
10. Ask the owner in Russian before changing any decision-class item. Present concise options with a recommendation, reason, and impact.
11. Apply technical-only repairs using existing project patterns and native OpenCode surfaces.
12. Run matching validators, tests, schema checks, plugin/hook checks, release/archive checks, installed-config checks, and instruction/memory freshness checks.
13. Synchronize durable docs and Serena memories from verified code/config state, then finish through `flow-post-task-sync` when durable artifacts changed.

## Non-Negotiables

- Current code, config, runtime checks, and verified GitHub state are the source of truth. Memories and docs are derived evidence.
- Do not edit ADR meaning, business logic, functional behavior, pricing, deployment targets, security posture, or data contracts without owner approval.
- Hooks and plugins stay bounded and deterministic. They may mark state; `ry-repair` performs the repair.
- Do not hide unresolved drift behind green summaries. Every blocked check names the blocker and next proof command.
- Do not report local repo, system config, Serena memory, or GitHub parity without evidence from `ry_repair_sync.py`, installed-config validators, current git state, and fullrepo/GitHub checks where applicable.

## Output

Report in Russian:

- Scope and source-of-truth map.
- Confirmed drift, grouped by severity.
- Technical repairs applied.
- Decision-class items left for owner approval.
- Exact validation commands and results.
- Docs/memory/fullrepo/git synchronization status.
