<!-- Memory Metadata
Last updated: 2026-05-17
Last commit: dd149aa chore(opencode): align plugin pin with runtime 1.15.3
Scope: AGENTS.md, opencode.json, VERSION, CHANGELOG.md, .opencode/, .serena/, references/, docs/, scripts/, .github/workflows/
Area: CORE
-->

# CORE-02-PROJECT-SHAPE

## Purpose

rldyour-opencode is the owner's personal OpenCode configuration marketplace. It provides OpenCode plugins, skills, agents, custom commands, configuration, reference docs, scripts, and Serena project knowledge.

## Source Of Truth

- `AGENTS.md`: project purpose, language policy, source-of-truth file list, domain boundaries, OpenCode conventions, validation commands, done criteria.
- `opencode.json`: authoritative runtime configuration loaded by OpenCode.
- `.opencode/`: project-level OpenCode agents, skills, commands, plugins, and plugin package metadata.
- `.serena/memories/`: verified project knowledge.
- `references/`: durable reference contracts consumed by skills and agents.
- `docs/`: marketplace operator guides and ADR archive.
- `scripts/`: validation, diagnostics, LSP, fullrepo, deploy-readiness, and sync helper scripts.

## Entry Points

- `opencode.json` uses `instructions: ["AGENTS.md"]`, so `AGENTS.md` is loaded as the project instruction file.
- `scripts/fullrepo_sync.sh`: manages agent-only context through the `fullrepo` orphan branch.
- `scripts/bootstrap_opencode.sh`: installs `.git/info/exclude` agent-only patterns.

## Current Behavior

- Repository version is `0.10.1` in `VERSION`; `CHANGELOG.md` has entries through `0.10.1` dated `2026-05-14`.
- Current branch is `main`; `git status --short --branch` reported `## main...origin/main` during this sync.
- Current directory layout includes 10 plugins, 9 agents, 10 commands, 32 skills, 16 references, 4 operator docs, 4 ADR files, 17 top-level scripts, and 9 pytest suites.
- `.opencode/package.json` provides the local OpenCode plugin dependency surface; `opencode.json.plugin` remains an empty list because local TypeScript plugins are auto-discovered from `.opencode/plugins/`.
- `.claude/CLAUDE.md` is a first-class agent-only project memory per `AGENTS.md`; it is not reduced to an `@AGENTS.md` pointer.

## Contracts And Data

- User-facing conversation with the owner is Russian unless explicitly requested otherwise.
- Repository artifacts are English: code, comments, docs, prompts, commits, memories, plans, and research archives.
- Technical identifiers stay ASCII and stable; plugin and skill names use kebab-case.
- Agent-only files include `AGENTS.md`, `.serena/`, `.opencode/`, `.claude/`, `.cursor/rules/`, `.agents/`, and related AI workflow directories.
- `scripts/fullrepo_sync.sh` runtime excludes include `.serena/cache/`, `.serena/project.local.yml`, `.serena/.serena_sync_state.json`, `.serena/.auto_sync_head`, `.opencode/local.json`, `.opencode/node_modules/`, `browser/`, and `node_modules/`.

## Invariants

- Do not duplicate subagents or commands into `opencode.json`; `.opencode/agents/*.md` and `.opencode/commands/*.md` are their single sources of truth.
- Do not commit secrets, runtime markers, browser artifacts, or local credentials.
- Normal branches should exclude agent-only files through `.git/info/exclude`; `fullrepo` carries portable agent-only context.

## Change Rules

- For whole-project initialization, bootstrap or restore agent-only context from `fullrepo` before relying on repo-local instructions and memories.
- Keep `AGENTS.md`, `.claude/CLAUDE.md`, durable docs, and Serena memories synchronized with changed behavior.
- Preserve current project patterns before inventing new directories, domains, or file roles.

## Verification

- `bash scripts/validate_config.sh`: validates `opencode.json`, skill/agent/command frontmatter, and `VERSION` semver.
- `python3 -m pytest scripts/tests/`: runs the repository validation test suites.
- `scripts/fullrepo_sync.sh status`: checks normal-branch/fullrepo sync state.
