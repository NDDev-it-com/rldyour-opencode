---
name: project-instructions-policy
description: "Политика project-инструкций: AGENTS.md, .claude/CLAUDE.md, REVIEW.md, ADRs (MADR 4.0.0). Используй для: правила проекта, инструкции, документация, ADR, долгоживущая документация. EN triggers: project rules, project instructions, ADR, MADR, write durable docs, update AGENTS.md, update CLAUDE.md, instruction policy."
---

# Project Instructions Policy

## Purpose

Keep durable project instructions useful for future sessions without turning them into chat history or generic advice.

## Rules

- Create or update `AGENTS.md` when durable root-level project rules, setup commands, quality gates, architecture constraints, deploy contracts, or workflow guidance change. `AGENTS.md` is the cross-tool standard root project-instruction file (see https://agents.md/).
- Keep `AGENTS.md` concise; it is loaded as a high-signal entry point and instruction size matters.
- Create or update project-specific instruction files for managed projects so the agent has first-class project memory.
- Keep instruction files optimized for the active agent, not as minimal re-exports. Reference agent-specific locations when relevant: configuration files, skill directories, command directories, memory directories, permission configs, health check tools, and status commands.
- Do not create root `CLAUDE.md` by default; `.claude/CLAUDE.md` is the project memory path.
- Create or update `REVIEW.md` when review-specific rules are durable and materially help future review agents.
- Create ADRs (MADR 4.0.0 format) for important architecture, technology, dependency, deployment, security, or irreversible design decisions.
- Repository docs, instructions, ADRs, memories, plans, comments, and commits are English. User-facing conversation with the user is Russian.
- Do not store secrets, personal tokens, local-only credentials, private cookies, or chat transcripts in docs.

## Agent-Only Files And tracked context

In normal product repositories, instruction files (`AGENTS.md`, `.claude/CLAUDE.md`, `REVIEW.md`) are agent-only context. They should be:

- Restored locally from `tracked context` branch via the project sync script.
- Ignored through `.git/info/exclude` (`tracked context` block installed automatically).
- Published to `tracked context` branch via sync workflow.
- Never committed to normal product branches (`main`, feature branches).

Repositories that are themselves agent tooling may intentionally track selected instruction templates as product files.

Read `references/project-instructions-and-adrs.md` before creating or updating durable instruction files.

## Anti-patterns

- Reduce `.claude/CLAUDE.md` to a thin `@AGENTS.md` import (violates project rule).
- Create root `CLAUDE.md` for new projects (`.claude/CLAUDE.md` is the preferred path).
- Commit `AGENTS.md`/`CLAUDE.md`/`REVIEW.md` into normal product branches (use tracked context).
- Store secrets / tokens / chat history in instruction docs.
- Skip ADR for irreversible decisions (architecture, framework, DB choice).
- Update instruction docs for mechanical formatting changes (only durable facts).