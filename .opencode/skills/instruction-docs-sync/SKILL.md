---
name: instruction-docs-sync
description: "Синхронизация AGENTS.md и .claude/CLAUDE.md из проверенных фактов проекта. Используй для: обнови инструкции проекта, AGENTS.md, документация, sync instructions. EN triggers: instruction-docs-sync, project docs sync, refresh AGENTS.md, update project instructions, CLAUDE.md sync, durable docs update."
---

# Instruction Docs Sync

## Purpose

Keep project instruction files current after meaningful work without creating a second source of truth or leaking agent-only files into normal branches.

This skill runs after Serena memory sync and before quality checks, commits, GitHub sync, and `fullrepo` publish.

## Required Files

- `AGENTS.md`: OpenCode-native project instructions. Source of truth for any AI agent working in the repository.

This file is agent-only in normal product repositories: keep it local, ignore it through `.git/info/exclude`, and publish it through `fullrepo`.

## Source Of Truth

Use only verified facts from:

- Current code, config, scripts, manifests, hooks, workflows, tests, and git diffs.
- Relevant Serena memories after they are current for the latest code.
- Commands that actually exist and checks that actually run.
- Official tool documentation when the file describes OpenCode or tool behavior.

Do not copy chat history, future plans, speculation, secrets, tokens, cookies, or local credentials.

## Workflow

1. Inspect changed files and recent commits to decide whether durable project facts changed.
2. Update `AGENTS.md` for OpenCode:
   - repository purpose and source-of-truth paths;
   - OpenCode-specific skill/agent/tool routing and plugin conventions;
   - setup, validation, release, deploy, git, and `fullrepo` commands;
   - concise engineering constraints and done criteria;
   - MCP server configuration and tool naming patterns (`mcp__<server>__<tool>`);
   - permission model and per-agent overrides.
3. Keep the file independently useful and optimized for OpenCode agents. Do not include instructions that only apply to other CLI tools unless the repository is explicitly multi-tool.
4. Validate that all referenced paths, commands, skills, and agents actually exist.
5. Let `flow-post-task-sync` commit normal tracked files, then publish agent-only instruction files through `fullrepo`.

## Freshness Rules

Review and update `AGENTS.md` when any meaningful task changes durable facts:

- Setup, install, bootstrap, doctor, validation, smoke, deploy, or release commands.
- Project architecture, module boundaries, generated artifacts, quality gates, or security policy.
- Skills, agents, commands, MCP definitions, LSP workflow, browser/design/security workflows, or git/fullrepo behavior.
- Repository-specific conventions that future OpenCode sessions must know before editing.
- Permission changes, new agents, or modified tool routing.

Do not update for:

- Purely mechanical formatting.
- Transient local state or temporary runtime markers.
- Facts already represented accurately.
- Changes that do not affect how an agent should interact with the repository.

## Validation Checklist

Before finalizing an `AGENTS.md` update:

- [ ] All source-of-truth paths referenced actually exist.
- [ ] All skills and agents referenced exist in `.opencode/skills/` and `.opencode/agents/`.
- [ ] All commands referenced exist in `.opencode/commands/` or `opencode.json`.
- [ ] All MCP tool names follow the `mcp__<server>__<tool>` pattern.
- [ ] No secrets, tokens, credentials, or local paths included.
- [ ] Description matches current project state, not aspirational state.
- [ ] Engineering rules reflect actual enforced constraints, not generic advice.

## Output

Report:

- `Instruction docs state`: required files present/missing, durable-change candidates, fullrepo policy.
- `Updated docs`: which instruction files changed and why.
- `Validation`: checklist result.
- `Fullrepo`: whether updated agent-only docs still need `fullrepo` publish.
