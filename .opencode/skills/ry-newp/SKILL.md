---
name: ry-newp
description: "Дизайн нового проекта: скептические вопросы, research, архитектура, ТЗ, ADR. Используй для: новый проект, ТЗ, проект с нуля, спроектируй, ARCHITECTURE.md. EN triggers: ry-newp, new project, design project from scratch, requirements, architecture docs, scaffold project, MADR ADR."
---

# ry-newp

## Purpose

Design a new project with enough rigor that implementation can start with clear architecture, technology choices, business logic, quality gates, and delivery plan.

## Workflow

1. Gather all provided context: prompt, docs, chats, requirements, screenshots, business constraints.
2. Ask skeptical Russian questions with options. Cover product scope, users, business logic, data, integrations, security, deployment, observability, tests, and constraints.
3. Research current best technologies and architecture patterns with `ry-explore`. Prefer Context7 MCP for official versioned framework docs, DeepWiki MCP for reference repo architecture, Grep MCP for real production patterns, and `web-research` for current landscape.
4. Use Sequential Thinking MCP (`sequential-thinking_*`) for non-trivial architecture and technology decisions.
5. Write planning docs under `.serena/newproj/<project>/` using `references/flow-lifecycle.md` as the lifecycle contract reference.
6. Ask for approval before creating any scaffold code.
7. If scaffold is approved, create the minimal useful project structure, commit atomically with Conventional Commits, and initialize Serena memories with verified facts only.

## Serena Memory Seeds

After scaffold approval and the first real commit, initialize Serena memories
from verified project facts only. At minimum seed `CONTEXT-01-CORE.md` for
current source-of-truth facts and `FUTURE-01-VISION.md` for future-shape
constraints. Propose ADR memories for non-obvious decisions, but do not write
ADR meaning without explicit owner approval.

## Output

Produce English project documents and Russian user-facing summaries.

Default docs:

- **HLO**: high-level overview — one-paragraph purpose, users, value.
- **Requirements**: functional and non-functional, with acceptance criteria.
- **Architecture**: layers, modules, data flow, integration points, deployment topology.
- **ADRs**: architecture decision records for each non-obvious choice with context, decision, and consequences.
- **Tech stack**: languages, frameworks, libraries, MCP servers, tooling — with version constraints and rationale.
- **API**: endpoints, payloads, auth, error contracts.
- **Data**: entities, fields, relationships, indexes, migrations strategy.
- **Infra**: hosting, CI/CD, environments, observability.
- **Security**: threat model, auth/authz, input validation, secrets management.
- **Testing**: unit, integration, E2E strategy, coverage targets.
- **Structure**: directory layout with purpose per directory.
- **Conventions**: naming, commits, branching, code style, review process.
- **Delivery plan**: milestones, dependencies, risk mitigation.

Each doc must be grounded in research evidence, not speculation. Link to sources for technology choices.
