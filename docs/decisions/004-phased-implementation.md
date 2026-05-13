# Phased Implementation Plan

> **Note (2026-05-13, supersession banner).** Example model IDs in code blocks
> below (`claude-sonnet-4-20250514`, `claude-haiku-4-20250514`,
> `claude-opus-4-20250514`) are historical and produce `ConfigInvalidError`
> against OpenCode v1.14.30+. Use the current registry IDs:
> `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-opus-4-7`.
> The ADR text itself is preserved unchanged — only the example IDs are
> obsolete. See `CHANGELOG.md` 0.5.0 and `.serena/memories/CORE_02_opencode_config.md`
> for migration context.

Based on commit history analysis of both rldyour-codex (108 commits) and rldyour-claudecode (87 commits).

## Phase 1: Foundation (Infrastructure + Config + AGENTS.md)

Commits modeled after: `aa53e1e` (codex bootstrap), `f43b3db` (claude bootstrap), `7950e5f` (MCP config), `18e5f63` (plugin metadata).

### Files to create:
1. `AGENTS.md` — OpenCode-specific root instructions
2. `opencode.json` — Master config (provider, model, MCP servers, LSP, agents, permissions, commands)
3. `.opencode/agents/flow-architecture-review.md`
4. `.opencode/agents/flow-quality-review.md`
5. `.opencode/agents/flow-consistency-review.md`
6. `.opencode/agents/flow-integration-review.md`
7. `.opencode/agents/flow-verification-review.md`
8. `.opencode/agents/flow-security-review.md`
9. `.opencode/agents/flow-memory-sync.md`
10. `.opencode/agents/ry-explore.md`
11. `.gitignore`
12. `README.md`
13. `VERSION`
14. `CHANGELOG.md`
15. `LICENSE`

## Phase 2: Skills (32 skills)

Commits modeled after: `8678292` (auto skill routing), `8ef14e3` (Russian routing), `0f7362b` (allowed-tools), `ef1b819` (bilingual descriptions).

### Domain: Flow (7 skills)
1. `.opencode/skills/ry-init/SKILL.md`
2. `.opencode/skills/ry-start/SKILL.md`
3. `.opencode/skills/ry-review/SKILL.md`
4. `.opencode/skills/ry-newp/SKILL.md`
5. `.opencode/skills/ry-deploy/SKILL.md`
6. `.opencode/skills/flow-post-task-sync/SKILL.md`
7. `.opencode/skills/instruction-docs-sync/SKILL.md`

### Domain: Serena (2 skills)
8. `.opencode/skills/serena-code-workflow/SKILL.md`
9. `.opencode/skills/serena-memory-sync/SKILL.md`

### Domain: Rules (7 skills)
10. `.opencode/skills/quality-first-engineering/SKILL.md`
11. `.opencode/skills/architecture-boundaries/SKILL.md`
12. `.opencode/skills/implementation-discipline/SKILL.md`
13. `.opencode/skills/dependency-compatibility-policy/SKILL.md`
14. `.opencode/skills/verification-quality-gates/SKILL.md`
15. `.opencode/skills/project-instructions-policy/SKILL.md`
16. `.opencode/skills/ry-rules-review/SKILL.md`

### Domain: Explore (2 skills)
17. `.opencode/skills/tech-research/SKILL.md`
18. `.opencode/skills/web-research/SKILL.md`

### Domain: Browser (3 skills)
19. `.opencode/skills/browser-tool-routing/SKILL.md`
20. `.opencode/skills/browser-validation/SKILL.md`
21. `.opencode/skills/browser-debug/SKILL.md`

### Domain: Design (5 skills)
22. `.opencode/skills/ry-design/SKILL.md`
23. `.opencode/skills/figma-to-code/SKILL.md`
24. `.opencode/skills/design-system-implementation/SKILL.md`
25. `.opencode/skills/fsd-frontend-architecture/SKILL.md`
26. `.opencode/skills/design-validation/SKILL.md`

### Domain: Security (2 skills)
27. `.opencode/skills/owasp-top-10-implementation/SKILL.md`
28. `.opencode/skills/ry-sec-review/SKILL.md`

### Domain: LSP (4 skills)
29. `.opencode/skills/lsp-routing/SKILL.md`
30. `.opencode/skills/lsp-health-check/SKILL.md`
31. `.opencode/skills/lsp-setup/SKILL.md`
32. `.opencode/skills/serena-lsp-integration/SKILL.md`

## Phase 3: Commands, References, Scripts

Commits modeled after: `3e2b525` (reviewer skills), `2082b5d` (docs), `ff14160` (operations scripts), `8123e46` (bootstrap/check scripts).

### Commands (6):
1. `.opencode/commands/ry-init.md`
2. `.opencode/commands/ry-start.md`
3. `.opencode/commands/ry-review.md`
4. `.opencode/commands/ry-newp.md`
5. `.opencode/commands/ry-deploy.md`
6. `.opencode/commands/ry-sync.md`

### References (16):
1. `references/init-context-pack.md`
2. `references/post-task-sync.md`
3. `references/flow-lifecycle.md`
4. `references/deploy-contract.md`
5. `references/reviewer-protocol.md`
6. `references/sources.md`
7. `references/context-sufficiency-gate.md`
8. `references/rules-policy.md`
9. `references/architecture-policy.md`
10. `references/dependency-policy.md`
11. `references/quality-gates.md`
12. `references/project-instructions-and-adrs.md`
13. `references/lsp-server-matrix.md`
14. `references/serena-lsp-integration.md`
15. `references/install-profiles.md`

### Scripts (3):
1. `scripts/validate_config.sh`
2. `scripts/bootstrap_opencode.sh`
3. `scripts/doctor_opencode.sh`

## Phase 4: Git, Serena, CI/CD

Commits modeled after: `018cc6e` (fullrepo agent context), `614b71e` (memory state), `8b7c897` (branch cleanup), `14f70e0` (local git guard), `bbb934b` (CI workflow).

1. `.serena/project.yml`
2. `.serena/memories/` (initial project state)
3. `.github/workflows/validate.yml`
4. Fullrepo sync documentation in AGENTS.md (adapted for OpenCode — no hooks, manual `/ry-sync` command)

## Implementation Order (within each phase)

Phase 1 is the critical path. Implement in this order:
1. `opencode.json` (all config — this is the core)
2. `AGENTS.md` (root instructions — this is what OpenCode reads first)
3. `.opencode/agents/*.md` (reviewer subagents — core workflow)
4. Root files (.gitignore, README, VERSION, CHANGELOG, LICENSE)

Phase 2 skills can be implemented in any order since they're independent.

Phase 3 depends on Phase 2 (commands reference skills).

Phase 4 is polish and CI.

## Key Design Decisions

### Hooks → Commands + Instructions

The 8 lifecycle hooks from Codex/Claude become:

| Hook | Codex/Claude | OpenCode |
|---|---|---|
| UserPromptSubmit | `user_prompt_submit.sh` (Serena advisory) | AGENTS.md instruction: "When the user writes a code-related prompt in Russian, automatically use serena-code-workflow skill" |
| PreToolUse:Bash | `prepare_auto_sync.sh` (Serena mark dirty) | AGENTS.md instruction: "After bash commands that modify files, consider serena-memory-sync" |
| PostToolUse:Bash | `mark_sync_required.sh` + `post_tool_use_commit_advice.sh` | AGENTS.md instruction: "After meaningful changes, commit atomically with Conventional Commits" |
| SessionStart | `session_start_context.sh` + `session_start_worktree_bootstrap.sh` | `/ry-init` command — manual bootstrap |
| Stop | `stop_memory_sync.sh` + `stop_post_task_sync.sh` | `/ry-sync` command — manual finalization. AGENTS.md: "Before ending a session, run /ry-sync to synchronize memories, docs, git, and fullrepo" |

### Reviewer Subagents

All 6 reviewers + flow-memory-sync become `.opencode/agents/*.md` with:
- `mode: subagent`
- `model: anthropic/claude-sonnet-4-20250514` (or user's choice)
- `temperature: 0.1` (focused, deterministic)
- `steps: 36` (for reviewers), `steps: 42` (for security), `steps: 36` (for memory-sync)
- `permission: { edit: "deny" }` (read-only reviewers)
- `hidden: true` (invoked via `@` or by primary agents, not shown in autocomplete)
- `color: blue/green/purple/orange/pink/red/yellow`

### ry-explore Agent

The deep research agent becomes:
- `mode: subagent`
- `model: anthropic/claude-opus-4-20250514` (or highest available)
- `temperature: 0.2`
- `steps: 90`
- `permission: { edit: "deny", bash: { "*": "ask" }, webfetch: "allow", websearch: "allow", lsp: "allow", skill: "allow" }`
- NOT hidden (available via `@ry-explore`)

### MCP Tools in Skill/Agent Prompts

In Claude Code, tools are referenced as `mcp__plugin_rldyour-mcps_<server>__<toolname>`.
In OpenCode, the pattern is `mcp__<servername>__<toolname>` (no `plugin_rldyour-mcps_` prefix).

This affects:
- serena-code-workflow skill (references `serena` tools)
- serena-memory-sync skill (references `serena` tools)
- flow-memory-sync agent (references `serena` tools)
- All MCP tool names in skill bodies

### Serena MCP Tool Names

Serena 1.3.0 with `--context=agent` exposes these tools (scoped to 28 tools):
- `list_memories`, `read_memory`, `write_memory`, `edit_memory`, `delete_memory`, `rename_memory`
- `get_symbols_overview`, `find_symbol`, `find_referencing_symbols`, `search_for_pattern`
- And others

In OpenCode's MCP naming: `mcp__serena__<tool_name>`

### fullrepo Branch Workflow

Same concept applies — agent-only files (AGENTS.md, .serena/, .opencode/, etc.) live on a `fullrepo` branch. But instead of hooks automating restore/publish:
- `/ry-init` command includes fullrepo bootstrap step
- `/ry-sync` command includes fullrepo publish step
- AGENTS.md documents the workflow and finish order