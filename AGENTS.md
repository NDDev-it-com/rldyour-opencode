# rldyour-opencode Agent Instructions

## Project Purpose

This repository is the owner's personal OpenCode configuration marketplace. It provides rldyour plugins, skills, agents, custom commands, configuration, and Serena project knowledge for the OpenCode AI coding agent.

## Language And Documentation

- User-facing communication with the owner is Russian unless explicitly requested otherwise.
- Repository files are English: docs, skill descriptions, agent prompts, scripts, comments, commits, Serena memories, plans, and research archives.
- Keep technical identifiers ASCII, stable, and kebab-case where applicable.
- Skill descriptions are Russian-leading (English keywords appended) for auto-routing.

## Source Of Truth

- `opencode.json`: master configuration — providers, models, agents, permissions, MCP servers, LSP, commands, tools, skills.
- `.opencode/agents/*.md`: subagent definitions with YAML frontmatter (mode, model, temperature, steps, permission, description, prompt).
- `.opencode/skills/*/SKILL.md`: on-demand skill definitions with name and description frontmatter.
- `.opencode/commands/*.md`: slash command templates.
- `references/*.md`: durable reference docs for skills and agents.
- `AGENTS.md`: this file — cross-tool root instructions for any AI agent working in this repository.
- `.serena/memories/*.md`: verified high-signal project knowledge.
- `VERSION` and `CHANGELOG.md`: release version and change history.

## OpenCode Conventions

### Skills
- Place in `.opencode/skills/<name>/SKILL.md`.
- Frontmatter: `name` (required, 1-64 chars, kebab-case, must match directory name), `description` (required, 1-1024 chars).
- OpenCode does NOT support `allowed-tools`, `disable-model-invocation`, `model`, `effort`, `maxTurns`, `paths`, `context`, or `agent` in skill frontmatter.
- Tool routing is controlled through agent `permission` config in `opencode.json`.
- Skills are loaded on-demand via the `skill` tool when an agent needs them.
- Skill discovery is automatic — agents see available skills and can call `skill({ name: "skill-name" })`.

### Agents
- Place in `.opencode/agents/<name>.md`.
- Frontmatter: `description` (required), `mode` (primary/subagent), `model`, `temperature`, `steps`, `permission`, `hidden`, `color`, `prompt`.
- Subagents are invoked via `@agent_name` in messages or via the Task tool by primary agents.
- Reviewer subagents use `mode: subagent`, `hidden: true`, `permission: { edit: "deny" }`.
- Permission keys support glob patterns: `bash: { "git diff": "allow", "*": "ask" }`.

### Commands
- Place in `.opencode/commands/<name>.md` or define in `opencode.json` → `command`.
- Frontmatter: `description`, `agent`, `model`.
- Body is the template sent to the agent.
- Commands are invoked via `/command-name` in the TUI.

### MCP Configuration
- All MCP servers are configured in `opencode.json` → `mcp` section (13 servers total).
- Local servers use `"type": "local"` with `"command"` array and optional `"environment"`.
- Remote servers use `"type": "remote"` with `"url"` and optional `"headers"`.
- Environment variables use `{env:VAR_NAME}` syntax.
- Tool names follow pattern `mcp__<servername>__<toolname>`.
- Use `bunx` for npm packages (never `npx`), `uvx` for Python packages, `dart` for Dart SDK.
- Pin exact versions for all packages to ensure reproducibility.
- `dart-flutter` is disabled by default (requires Dart SDK 3.9+ on PATH); enable per-project as needed.
- `context7` supports higher rate limits with `CONTEXT7_API_KEY`; works without key at lower limits.

#### MCP servers (13)

| Server | Type | Launcher | Version | Purpose |
|---|---|---|---|---|
| serena | local | uvx | 1.3.0 | Semantic code navigation, analysis, editing |
| sequential-thinking | local | bunx | 2025.12.18 | Structured reasoning and planning |
| playwright | local | bunx | 0.0.75 | Browser automation, UI validation |
| chrome-devtools | local | bunx | 0.25.0 | Chrome DevTools diagnostics |
| context7 | remote | https | — | Current library documentation |
| deepwiki | remote | https | — | Repository documentation |
| grep | remote | https | — | Search across public GitHub repos |
| semgrep | local | uvx | 1.162.0 | Static analysis and security |
| shadcn | local | bunx | 4.7.0 | shadcn/ui registry access |
| dart-flutter | local | dart | — | Dart/Flutter project support (disabled by default) |
| figma | remote | https | — | Figma design context |
| github | remote | https | — | GitHub Copilot MCP (requires PAT) |
| openai-docs | remote | https | — | Official OpenAI/Codex documentation |

### Plugins
- Place in `.opencode/plugins/` (project-level) or `~/.config/opencode/plugins/` (global).
- TypeScript/JavaScript modules exporting plugin functions.
- Events: `session.created`, `session.idle`, `session.compacted`, `file.edited`, `lsp.updated`, `message.updated`, `tool.execute.before`, `tool.execute.after`, `experimental.session.compacting`, `shell.env`, `tui.prompt.append`, `tui.command.execute`, `tui.toast.show`, `permission.asked`, `permission.replied`.
- Dependencies go in `.opencode/package.json` — OpenCode runs `bun install` at startup.
- rldyour plugins: `ry-bootstrap.ts` (compaction context), `ry-env-protection.ts` (block sensitive reads), `ry-shell-strategy.ts` (non-interactive shell, env injection), `ry-sync-reminder.ts` (idle session reminder).

### Permissions
- Global permissions in `opencode.json` → `permission`.
- Per-agent overrides in `opencode.json` → `agent.<name>.permission`.
- Values: `"allow"`, `"ask"`, `"deny"`, or object with glob patterns.
- Key permission keys: `read`, `edit`, `glob`, `grep`, `bash`, `task`, `webfetch`, `websearch`, `lsp`, `skill`, `question`.

## Plugin Routing

Use rldyour skills and agents automatically when the task matches their scope:

- `serena-code-workflow`: repository understanding, code exploration, semantic symbol work, refactors, code review.
- `serena-memory-sync`: fact-only .serena memories synchronization.
- `ry-init` / `ry-start` / `ry-review` / `ry-newp` / `ry-deploy`: SDLC workflow commands.
- `ry-explore` (@ry-explore): deep multi-source research with Context7, DeepWiki, Grep, web search.
- `quality-first-engineering`, `architecture-boundaries`, `implementation-discipline`, `dependency-compatibility-policy`, `verification-quality-gates`, `project-instructions-policy`: engineering rules.
- `ry-rules-review`: audit implementation against rldyour rules.
- `lsp-routing`, `lsp-health-check`, `lsp-setup`, `serena-lsp-integration`: language server workflows.
- `browser-tool-routing`, `browser-validation`, `browser-debug`: browser workflows.
- `ry-design`, `figma-to-code`, `design-system-implementation`, `fsd-frontend-architecture`, `design-validation`: design workflows.
- `owasp-top-10-implementation`, `ry-sec-review`: security workflows.
- `tech-research`, `web-research`: research workflows.

The owner normally writes prompts in Russian. When a helper skill matches the Russian intent, use the helper skill automatically instead of waiting for the owner to name it.

## Tool Priority

| Task | Primary | Fallback | Reason |
|---|---|---|---|
| Symbol search | Serena `find_symbol` | `grep` | LSP-aware structure |
| Code structure | Serena `get_symbols_overview` | targeted file read | Avoid full-file reads |
| Code relationships | Serena `find_referencing_symbols` | `grep` | Trace callers |
| Symbol editing | Serena symbol tools | `edit` tool | Precise and structure-aware |
| Technical docs | Context7 MCP | `websearch` | Official and versioned |
| Repo architecture | DeepWiki MCP | source read | Public repo structure |
| Code patterns | Grep MCP | `websearch` | Real production usage |
| Planning | Sequential Thinking MCP | explicit local plan | Reduces decision errors |
| Browser validation | Playwright MCP | Chrome DevTools MCP | Reproduce and prove |
| Security review | Semgrep + manual review | `grep` | Scanner output must be validated |

## OpenCode Built-in Tools

OpenCode provides these built-in tools (no MCP needed): `bash`, `edit`, `write`, `read`, `grep`, `glob`, `apply_patch`, `lsp` (experimental), `skill`, `todowrite`, `webfetch`, `websearch`, `question`.

MCP tools follow the `mcp__<servername>__<toolname>` naming pattern. For example:
- Serena: `mcp__serena__find_symbol`, `mcp__serena__get_symbols_overview`, etc.
- Context7: `mcp__context7__resolve-library-id`, `mcp__context7__get-library-docs`
- DeepWiki: `mcp__deepwiki__*`
- Grep: `mcp__grep__*`

## Engineering Rules

- Quality and correctness are higher priority than speed.
- No hacks, temporary workarounds, fake implementations, or swallowed errors.
- Keep systems synchronized across code, docs, configuration, git history, and Serena memories.
- Prefer low semantic entropy: reuse existing patterns, keep boundaries clear.
- Code is the source of truth. Memories and docs must reflect verified code.
- Use Sequential Thinking MCP for non-trivial decisions.
- Conventional Commits for all changes. Atomic commits per logical unit.
- Never commit secrets, runtime markers, browser artifacts, or local credentials.

## LSP

OpenCode has 35+ built-in LSP servers that auto-start when file extensions are detected. Enabled in `opencode.json` with `"lsp": {}` (object = built-ins enabled + custom overrides).

Custom LSP servers added for coverage beyond built-ins:

| Key | Server | Extensions | Notes |
|---|---|---|---|
| `ruff` | `ruff server` | `.py`, `.pyi` | Python linter companion to pyright |
| `vscode-html` | `vscode-html-language-server --stdio` | `.html`, `.htm` | From vscode-langservers-extracted |
| `vscode-css` | `vscode-css-language-server --stdio` | `.css`, `.scss`, `.sass`, `.less` | From vscode-langservers-extracted |
| `vscode-json` | `vscode-json-language-server --stdio` | `.json`, `.jsonc` | From vscode-langservers-extracted |
| `docker` | `docker-language-server start --stdio` | `.dockerfile` | Dockerfile/Compose support |
| `taplo` | `taplo lsp stdio` | `.toml` | TOML schema support |
| `marksman` | `marksman server` | `.md`, `.mdx`, `.markdown` | Markdown intelligence |
| `qmlls` | `qmlls` | `.qml` | Qt QML support (optional) |

Runtime rules for LSP skills:
- Never start `stdio` language servers manually; OpenCode manages their lifecycle.
- Never use `bunx`/`uvx` as runtime for long-lived LSP servers; use stable local executables.
- Use `lsp-routing` skill for language-server selection guidance.
- Use `lsp-health-check` skill to verify LSP commands and project prerequisites.
- Use `lsp-setup` skill only on explicit user request (brew-first install policy).
- Use `serena-lsp-integration` skill to align Serena MCP with supported language keys.

## Serana Memories And Project Knowledge

- Store durable facts in `.serena/memories/` with the project memory metadata format.
- Memories are facts only: exact paths, entry points, behavior, contracts, invariants.
- After meaningful changes, synchronize Serena memories before final delivery.
- Use `serena-memory-sync` skill or `@flow-memory-sync` agent for fact-only memory updates.

## Git And Sync

- Keep `main` synchronized with `origin/main` unless working on an explicit branch.
- Prefer atomic commits with Conventional Commits.
- Before ending a session, run `/ry-sync` to:
  1. Verify Serena memories are current for HEAD.
  2. Update AGENTS.md from verified code state.
  3. Run applicable quality checks.
  4. Commit atomically and push.
  5. Publish agent-only files to `fullrepo` branch if applicable.
- `fullrepo` is the standard branch for portable agent-only context. Normal branches should exclude AGENTS.md, .serena/, .opencode/ agents/skills/commands, and similar AI workflow files through `.git/info/exclude`.
- Agent-only files include: project-root `AGENTS.md`, `.serena/` knowledge, `.opencode/` agents/skills/commands, `.claude/`, `.cursor/rules/`, `.agents/`, and similar AI workflow directories.

## Done Criteria

- `opencode.json` is valid JSON with correct schema.
- All agent and skill files have required frontmatter fields.
- Skill names are valid (1-64 chars, kebab-case, matching directory name).
- Agent descriptions are present and specific (1-1024 chars).
- `git status` is clean of non-agent files.
- Serena memories reflect current code state.
- Conventional commits for source/docs/Serena knowledge are separate when it improves history clarity.