# Project Instructions And ADRs

## AGENTS.md

`AGENTS.md` is the cross-tool standard root project-instruction file (see https://agents.md/). Create or update it when durable root-level project facts change:

- Setup commands.
- Quality gates.
- Architecture constraints.
- Project-specific coding rules.
- Deploy contracts.
- Review rules.
- Tooling and generated artifact rules.

Keep it concise. It is loaded as a high-signal entry point at session start, so it should contain high-signal project rules only.

For normal product repositories, project-root `AGENTS.md` is agent-only context. Keep it local and in the `fullrepo` branch, and add it to `.git/info/exclude` through the rldyour fullrepo workflow instead of tracking it in normal branches. Repositories that are themselves agent tooling may intentionally track instruction templates as product artifacts.

## opencode.json And .opencode/

OpenCode reads project configuration from `opencode.json` at the repository root. It defines providers, models, agents, permissions, MCP servers, LSP settings, commands, and tools.

`.opencode/` contains agent definitions (`.opencode/agents/*.md`), skill definitions (`.opencode/skills/*/SKILL.md`), and command templates (`.opencode/commands/*.md`).

Update `opencode.json` and `.opencode/` files when:

- Agent definitions, permissions, or models change.
- Skill or command templates change.
- MCP server configuration changes.
- Quality gate commands change.

For normal product repositories, `.opencode/` files are agent-only context and follow the same `fullrepo` branch policy as `AGENTS.md`.

## REVIEW.md

Create or update `REVIEW.md` when review-specific rules are durable:

- Always-check areas.
- Architecture boundaries.
- Security-sensitive paths.
- Test expectations.
- Known generated files to ignore.
- Project-specific false positives.

## ADRs (MADR 4.0.0 — May 2026 canonical)

Use the **MADR 4.0.0** template from [adr.github.io/madr](https://adr.github.io/madr/). Released September 2024, stable in 2026.

Store ADRs in the project-standard location when one exists. Otherwise prefer `docs/adr/`.

### MADR 4.0.0 fields

- **Title** (`# <ADR number>: <short noun phrase>`).
- **Status**: proposed / rejected / accepted / deprecated / superseded by [...].
- **Date**: when the decision was last updated.
- **Decision-Makers**: list of people involved.
- **Consulted**: list of people whose opinions were sought.
- **Informed**: list of people kept up to date.
- **Context and Problem Statement**: describe the problem and constraints.
- **Decision Drivers**: list of forces / requirements / quality attributes.
- **Considered Options**: list of options.
- **Decision Outcome**: chosen option and justification.
- **Consequences**: positive and negative consequences in one combined section (changed in MADR 3.0.0).
- **Confirmation**: how the decision is confirmed (tests, monitoring, review).
- **Pros and Cons of the Options** (optional).
- **More Information** (optional, links).

Use the **bare** template variant for minimal overhead, **full** variant for important decisions.

### When to write an ADR

- New architecture style or major boundary change.
- New framework, database, message broker, auth strategy, deployment model.
- Critical dependency choice or version pin.
- Intentional deviation from project defaults (FSD/VSA/Hexagonal).
- Breaking public API or contract change.
- Long-lived tradeoff that future agents must preserve.

## Agent-Only Files And Fullrepo

Agent-only files that reveal or preserve AI workflow state should not be committed to normal project branches. Store them locally, ignore them through `.git/info/exclude`, and publish them to the `fullrepo` branch.

Default agent-only paths include:

- `AGENTS.md`, `REVIEW.md`, and other root instruction files.
- `.serena/project.yml`, `.serena/memories/`, `.serena/plans/`, `.serena/research/`, `.serena/newproj/`, and `.serena/deploy/`.
- `.opencode/agents/`, `.opencode/skills/`, `.opencode/commands/`.
- `.claude/`, `.cursor/rules/`, `.agents/`, `.github/instructions/`, and `.github/prompts/`.

Never publish runtime markers, caches, local env files, browser evidence, secrets, tokens, cookies, or credentials to `main` or `fullrepo`.
