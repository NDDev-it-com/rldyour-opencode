---
name: ry-init
description: "Инициализируй контекст проекта: read-only scoped discovery с Serena, tracked context, архитектура, отчёт. Используй для: изучи проект, инициализируй контекст, разбери репозиторий, scope/sphere/module discovery. EN triggers: ry-init, init project, init scope, initialize context, project onboarding, context pack, study repo, learn project."
---

# ry-init

## Purpose

Build a verified mental model of the requested project scope before implementation. If the scope is a sphere such as backend or mobile UI, inspect the entire sphere and all integration points needed to understand how it works end to end.

`ry-init` is read-only for project knowledge by default. It reads tracked agent context directly from `main`, but it must not create, edit, or delete Serena memories unless the user explicitly asks to update/synchronize memories or an active stale-memory hook requires synchronization.

## Workflow

1. Run git sync audit when available. Inspect dirty work, old branches, and worktrees. If code is correct and consistent, synchronize it into `main`, push, and remove merged branches/worktrees. If risky, explain the issue in Russian and ask the user with concrete options.
2. Resolve effective project policy with `scripts/project_flow_policy.py --json` when available. Treat durable agent context as normal tracked source and runtime-local state as ignored.
3. Read `references/init-context-pack.md` and use it as the required context-pack contract.
4. Use `serena-code-workflow`: check onboarding, list memories, read relevant memories, and use Serena semantic tools (`serena_find_symbol`, `serena_get_symbols_overview`, `serena_find_referencing_symbols`) before raw file reads.
5. Map the requested scope deeply enough to understand modules, layers, symbols, DB fields, schemas, APIs, generated artifacts, configs, tests, and integration paths.
6. Use `lsp-routing` or `lsp-health-check` when language server support affects understanding. OpenCode has 30+ built-in LSP servers that auto-start when file extensions are detected.
7. Use `tech-research` or `web-research` only for unclear technology, architecture, or current best-practice questions. Prefer Context7 MCP (`context7_resolve-library-id`, `context7_get-library-docs`) for official versioned docs, DeepWiki MCP for public repo architecture, and Grep MCP for real production usage patterns.
8. Use Sequential Thinking MCP (`sequential-thinking_*`) for non-trivial architectural decisions.
9. Synthesize a Russian report with exact source-of-truth paths, current behavior, data/contracts, integration points, quality gates, risks, gaps, and what OpenCode can now safely change.
10. Do not run `serena-memory-sync` automatically. If initialization discovers useful durable facts that are missing from memories, report them under `Memory candidates (not written)` with exact source paths and ask before writing. Only run `serena-memory-sync` during `ry-init` when the user explicitly requested memory sync/update or a stale-memory hook requires it.

## Role Declaration (Orchestrator)

Session role is declarative, not auto-detected:

- If the user's init request explicitly declares this terminal the orchestrator
  (for example "я оркестратор", "this terminal is the orchestrator"), verify the
  preconditions: macOS, a cmux session (`CMUX_WORKSPACE_ID`/`CMUX_SURFACE_ID`
  present), and the orchestrator skills installed. When they hold, adopt the
  orchestrator duties from the `cmux-orchestrator` skill for the rest of the
  session: own user communication, task decomposition, delegation, final
  validation, and sync. When a precondition fails, say which one and continue
  in standard mode.
- Without that explicit declaration, always run in standard mode - never
  auto-activate orchestrator behavior from environment, policy, or guesswork.
- Worker terminals are not declared by the user: they are machine-identified by
  the launcher/layout environment (`RLDYOUR_AGENT_ROLE=worker`,
  `RLDYOUR_WORKER_ID`) and follow the `cmux-worker` skill.

## Scope Rules

- Empty scope means whole project.
- Sphere scope means the whole sphere plus integration points.
- Feature scope means trace all layers touched by that feature.
- Ambiguous scope means ask the user with 2-3 options.
- Do not stop at file lists. The initialized context must explain how relevant code works end to end.
- For database-backed or API work, include fields, schemas, migrations, payloads, and caller/client paths.
- For UI/client work, include routes/screens/components, state, API calls, design-system constraints, browser-visible behavior, and tests.
- If agent-context files such as `AGENTS.md`, `.serena/*`, `.opencode/agents/*`, `.opencode/skills/*`, `.opencode/commands/*`, `.claude/*`, `.cursor/rules/*`, or `.agents/*` are needed for context, read them as normal source files when present and report missing required context explicitly.
- Runtime snapshots, server log summaries, health-check timestamps, current container status, and one-off audit observations are report material, not Serena memory material, unless they reveal a stable code/config contract.

## Output

Report in Russian:

- Scope initialized.
- Git/GitHub/worktree state.
- Architecture and data flow.
- Key files and symbols.
- Data models, DB fields, schemas, API contracts, config/env keys, and generated artifacts.
- Integration points.
- Tests, LSP/check commands, browser/security/design evidence when relevant.
- Known risks and gaps.
- Memory candidates (not written), only when useful durable facts were found and memory sync was not explicitly requested.
- Ready-for tasks.
