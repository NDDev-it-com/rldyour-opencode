---
name: ry-start
description: "Полный lifecycle задачи: init, research, plan, implement, verify, review, commit, sync. Используй для: реализуй задачу, доработай, исправь качественно, сделай фичу, end-to-end, доведи до конца. EN triggers: ry-start, full SDLC, implement task, ship feature, build feature, complete lifecycle, end-to-end task, reviewer pipeline."
---

# ry-start

## Purpose

Implement a task to a high-quality, scalable, synchronized state. Speed is secondary to correctness, consistency, maintainability, and clean git history.

## Workflow

1. If context is missing, run a scoped `ry-init` automatically.
2. Understand the prompt. For ambiguity, ask concise Russian questions with options.
3. Research code through Serena memories and semantic tools (`serena_find_symbol`, `serena_get_symbols_overview`, `serena_find_referencing_symbols`).
4. Research current docs, patterns, and alternatives through `ry-explore`. Prefer Context7 MCP for official versioned docs, DeepWiki MCP for public repo architecture, and Grep MCP for real production usage patterns.
5. Read `references/context-sufficiency-gate.md` and pass the gate before editing code.
6. Write a detailed plan. Verify each plan item against code using Serena before editing.
7. Create or use a feature branch/worktree. Use stacked PRs only when the task naturally splits into independent logical PRs.
8. Implement strictly by plan, adapting only after code evidence. Make frequent atomic Conventional Commits.
9. Provide progress checkpoints after meaningful milestones or every 2-3 completed plan groups.
10. Fix all issues in touched scope plus affected integration path. If wider technical debt is found, ask whether to expand scope.
11. Run quality gates using project scripts, OpenCode LSP (auto-starts for detected file extensions), and detected stack checks. Use `verification-quality-gates` skill.
12. Trigger browser validation for UI/browser-visible work unless auth blocks it; if auth blocks, report the limitation and use available evidence. Use `browser-tool-routing` and `browser-validation` skills.
13. Trigger security review for security-sensitive changes or explicit user request. Use `owasp-top-10-implementation` and `ry-sec-review` skills.
14. Run the review phase. Invoke up to six parallel reviewer subagents in a single Task fan-out (each with a self-contained prompt — they do not share context):
    - `@flow-architecture-review` — boundaries, dependency direction, public API shape, data flow.
    - `@flow-quality-review` — correctness, edge cases, error handling, resource lifecycle.
    - `@flow-consistency-review` — naming, style, imports, project conventions.
    - `@flow-integration-review` — cross-module contracts, schemas, configs, backward compatibility.
    - `@flow-verification-review` — tests, quality gates, browser/server evidence.
    - `@flow-security-review` — OWASP, auth/authz, injection, secrets (only when the touched scope is security-sensitive or the owner asks explicitly; this track runs `steps: 42` instead of `36` because it does a variant-hunt sweep on confirmed findings).
    Consolidate findings via Severity × Disposition (see `references/reviewer-protocol.md`); fix `must-fix` + `should-fix` items; rerun only the reviewer tracks that reported issues.
15. Run `flow-post-task-sync` before final response.

## Automatic Helper Routing

The owner normally writes prompts in Russian. `ry-start` must route helper skills automatically instead of waiting for explicit helper skill names:

| Russian intent pattern | Helper skills |
|---|---|
| изучи код, посмотри проект, реализуй, доработай, исправь, рефакторинг, ревью, архитектура, файлы, директории, symbols, implementation scope | `serena-code-workflow`, `lsp-routing`, `quality-first-engineering`, `implementation-discipline` |
| исследуй интернет, изучи в интернете, посмотри документацию, best practices, migration, API behavior, framework/library setup, MCP/tool sources | `tech-research` (Context7, DeepWiki, Grep MCP), then `web-research` for broader sources |
| проверь в браузере, визуально, UI, адаптив, скриншот, pixel-perfect, user flow, business-logic checks | `browser-tool-routing`, `browser-validation` |
| консоль, сеть, runtime, layout, hydration, Lighthouse, performance, browser-only failures | `browser-debug` |
| Figma, дизайн, UI, верстка, дизайн-система, shadcn/ui, ReactBits, FSD, tokens, pixel-perfect design | `ry-design`, `figma-to-code`, `design-system-implementation`, `fsd-frontend-architecture`, `design-validation` |
| auth/authz/API/input/file/dependency/config/secrets/payment/admin/external-integration | `owasp-top-10-implementation` |
| security review request, sensitive scope | `ry-sec-review`, `flow-security-review` in review phase |
| завершение, финализация, durable code/config/docs/memory changes produced | `verification-quality-gates`, `serena-memory-sync`, `flow-post-task-sync` |

## Context Sufficiency

Do not implement from a shallow prompt. Before editing, the model must know the relevant architecture, files, symbols, DB/schema/API/config contracts, tests, integration paths, current project patterns, and current external API/framework guidance needed for the task.

If the model cannot answer the gate questions in `references/context-sufficiency-gate.md`, it must gather more evidence through Serena, LSP, `ry-explore`, browser/security/design workflows, or ask the owner with options. This is a quality guard, not a hard blocker: the correct response is to enrich context until implementation is safe.

## Subagent Permission

Invoking `ry-start` is the owner's explicit permission to use parallel reviewer subagents during the review phase. Reviewer track skills are orchestrated by this command, not broad implicit-entry skills. Prompts must be self-contained and read-only for reviewers. Reviewer subagents use `mode: subagent`, `hidden: true`, `permission: { edit: "deny" }` as defined in `.opencode/agents/`.

## Non-Negotiables

- No hacks, temporary workarounds, or untracked debt in touched scope.
- No fake green checks. If a check cannot run, say why.
- No silent destructive git actions. Branch/worktree cleanup requires verified merged state.
- No secrets in commits, logs, docs, memories, or prompts.
