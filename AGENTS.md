# rldyour-opencode Agent Instructions

## Project Purpose

This repository is the owner's personal OpenCode configuration marketplace. It provides rldyour plugins, skills, agents, custom commands, configuration, and Serena project knowledge for the OpenCode AI coding agent.

## Language And Documentation

- User-facing communication with the owner is Russian unless explicitly requested otherwise.
- Repository files are English: docs, skill descriptions, agent prompts, scripts, comments, commits, Serena memories, plans, and research archives.
- Keep technical identifiers ASCII, stable, and kebab-case where applicable.
- Skill descriptions are Russian-leading (English keywords appended) for auto-routing.

## Source Of Truth

- `opencode.json`: master configuration — providers, models, primary agents (build, plan), permissions, MCP servers, LSP, plugins, watcher, compaction.
- `.opencode/agents/*.md`: single source of truth for subagent definitions (frontmatter + prompt body). Do NOT duplicate in `opencode.json`.
- `.opencode/skills/*/SKILL.md`: on-demand skill definitions with name and description frontmatter.
- `.opencode/commands/*.md`: single source of truth for slash command definitions (frontmatter + template body). Do NOT duplicate in `opencode.json`.
- `.opencode/plugins/*.ts`: OpenCode plugin event handlers.
- `references/*.md`: durable reference docs consumed by skills and agents.
- `docs/*.md`: durable operational guides for marketplace operators (release, dependency-updates, rollback-restore).
- `docs/decisions/*.md`: architecture decision archive (MADR-style ADRs; moved from former `thinking/` directory).
- `AGENTS.md`: this file — cross-tool root instructions for any AI agent working in this repository.
- `.serena/memories/*.md`: verified high-signal project knowledge.
- `VERSION` and `CHANGELOG.md`: release version and change history.

## Domain Boundaries

Each skill and agent belongs to exactly one domain. Cross-domain overlap is forbidden.

| Domain | Skills | Agents | Commands |
|---|---|---|---|
| Flow (lifecycle) | flow-post-task-sync, ry-init, ry-start, ry-review, ry-newp, ry-deploy | flow-*review, flow-memory-sync | ry-init, ry-start, ry-review, ry-newp, ry-deploy, ry-sync |
| Serena (MCP) | serena-code-workflow, serena-memory-sync, serena-lsp-integration | — | — |
| Rules | quality-first-engineering, architecture-boundaries, implementation-discipline, dependency-compatibility-policy, verification-quality-gates, project-instructions-policy, ry-rules-review | — | ry-rules-review |
| Explore | tech-research, web-research | ry-explore | ry-explore |
| Browser | browser-tool-routing, browser-validation, browser-debug | — | — |
| Design | ry-design, figma-to-code, design-system-implementation, fsd-frontend-architecture, design-validation | — | ry-design |
| Security | owasp-top-10-implementation, ry-sec-review | — | ry-sec-review |
| LSP | lsp-routing, lsp-health-check, lsp-setup | — | — |
| Docs sync | instruction-docs-sync | — | — |
| Config | — | customize-opencode | — |

Rules:
- Only Serena domain may invoke MCP tools matching the `serena_*` ID pattern (e.g. `serena_find_symbol`, `serena_get_symbols_overview`).
- Only LSP domain may invoke LSP skills directly.
- Only Browser domain may invoke Playwright / Chrome DevTools MCP tools (`playwright_*`, `chrome-devtools_*`).
- Flow domain orchestrates other domains via skills and subagents.
- Security domain may invoke Semgrep MCP tools (`semgrep_*`).

## OpenCode Conventions

### Skills
- Place in `.opencode/skills/<name>/SKILL.md`.
- Required frontmatter: `name` (1-64 chars, kebab-case, must match directory name), `description` (1-1024 chars).
- Optional frontmatter accepted by OpenCode v1.14: `license`, `compatibility`, `metadata` (string-to-string map). Unknown fields are ignored silently.
- Forbidden in OpenCode skills: `allowed-tools`, `disable-model-invocation`, `model`, `effort`, `maxTurns`, `paths`, `context`, `agent`. These are Claude Code / Codex leftovers and are not honored.
- Tool routing is governed by agent `permission` config (global in `opencode.json` or per-agent in `.opencode/agents/<name>.md`), never by skill frontmatter.
- Skills are loaded on-demand via the built-in `skill` tool — agents see name + description and invoke via `skill({ name: "skill-name" })`.

### Agents
- Place in `.opencode/agents/<name>.md`.
- Frontmatter: `description` (required, 1-1024 chars), `mode` (primary/subagent), `model`, `temperature`, `steps`, `permission`, `hidden`, `color`, `prompt` (or in markdown body).
- `color` must match `^#[0-9a-fA-F]{6}$` (hex) or one of the enum values `primary`, `secondary`, `accent`, `success`, `warning`, `error`, `info`. Named CSS colors (`blue`, `red`, …) are rejected by OpenCode v1.14.
- Subagents are invoked via `@agent_name` in messages or via the Task tool by primary agents.
- Reviewer subagents use `mode: subagent`, `hidden: true`, `permission: { edit: "deny" }`.
- Permission keys support glob patterns: `bash: { "*": "ask", "git diff": "allow" }`.
- Subagents defined ONLY in `.opencode/agents/*.md` — never duplicated in `opencode.json`.
- Primary agents (build, plan) with just permissions can stay in `opencode.json`.

#### OpenCode built-in agents (do not redefine, do not invoke as if ours)

OpenCode v1.14 ships these primary + subagent built-ins; they are always present at runtime regardless of `.opencode/agents/`:

- `build` (primary, default) — all tools enabled.
- `plan` (primary) — restricted, `edit`/`bash` default to ask.
- `general` (subagent) — full tool access for multi-step tasks.
- `explore` (subagent, read-only) — codebase exploration.
- `scout` (subagent, read-only; added in OpenCode v1.14.42) — external docs lookup and dependency-source inspection. Complementary to our `@ry-explore` (which leans on Context7/DeepWiki/Grep MCP via Opus 4.7).

Our `.opencode/agents/customize-opencode.md` is a **custom subagent**, distinct from the **built-in `customize-opencode` skill** added in OpenCode v1.14.46 (an internal config-safety skill triggered when an agent edits `opencode.json`). Agent and skill share a namespace prefix but are separate runtime entities; verified non-conflicting by `scripts/tests/test_opencode_resolve.py::test_each_agent_resolves`.

### Commands
- Place in `.opencode/commands/<name>.md`.
- Frontmatter: `description`, `agent`, `model`, `subtask` (optional, forces subagent invocation).
- Body is the template sent to the agent. Supports `$ARGUMENTS`, `$1`/`$2`/..., `` !`command` `` for shell output, `@file` for file references.
- Commands defined ONLY in `.opencode/commands/*.md` — never duplicated in `opencode.json`.

### MCP Configuration
- All MCP servers are configured in `opencode.json` → `mcp` section (13 servers total).
- Local servers use `"type": "local"` with `"command"` array and optional `"environment"`.
- Remote servers use `"type": "remote"` with `"url"` and optional `"headers"`.
- Environment variables use `{env:VAR_NAME}` syntax.
- Tool names follow the OpenCode v1.14.48 pattern `<server>_<tool>` (single underscore separator). Server names are sanitised first — every char outside `[a-zA-Z0-9_-]` is replaced with `_`, dashes are preserved. Example: `serena_find_symbol`, `chrome-devtools_list_console_messages`, `context7_resolve-library-id`. The Claude Code-style double-underscore prefix `mcp__<server>__<tool>` does NOT match the runtime and silently disables any plugin that uses it.
- Use `bunx` for npm packages (never `npx`), `uvx` for Python packages, `dart` for Dart SDK.
- Pin exact versions for all packages to ensure reproducibility.
- `context7` supports higher rate limits with `CONTEXT7_API_KEY`; works without key at lower limits.
- Required env vars documented in `.env.example`.

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
| dart-flutter | local | dart | — | Dart/Flutter project support |
| figma | remote | https | — | Figma design context |
| github | remote | https | — | GitHub Copilot MCP (requires PAT) |
| openai-docs | remote | https | — | Official OpenAI/Codex documentation |

### Plugins
- Place in `.opencode/plugins/` (project-level) or `~/.config/opencode/plugins/` (global). npm packages listed in `opencode.json.plugin` install via Bun at startup; this repo's `plugin: []` is intentional — only local TypeScript plugins are used.
- Plugin file exports a named `Plugin` from `@opencode-ai/plugin`. Plugin factory receives `PluginInput = { client, project, directory, worktree, experimental_workspace, serverUrl, $ }` and returns a `Hooks` object.
- Server-side hook keys available in `@opencode-ai/plugin` v1.14.48 (verified against `.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts`):
  - Lifecycle / observation: `event` (catch-all with `event.type` discriminator from the SDK `Event` union — covers session, file, message, todo, lsp, command, installation, server etc.), `config`.
  - Tool registration / inspection: `tool` (register custom tools), `tool.definition`, `tool.execute.before`, `tool.execute.after`.
  - Shell and permission: `shell.env`, `permission.ask`.
  - Chat pipeline: `chat.message`, `chat.params`, `chat.headers`.
  - Command: `command.execute.before`.
  - Auth / provider extension: `auth`, `provider`.
  - Experimental: `experimental.chat.messages.transform`, `experimental.chat.system.transform`, `experimental.session.compacting`, `experimental.compaction.autocontinue`, `experimental.text.complete`.
- TUI-side hooks (`tui.prompt.append`, `tui.command.execute`, `tui.toast.show`) live under `@opencode-ai/plugin/tui.d.ts` and require a different plugin shape (`PluginModule.tui`). They are NOT used in this repo's server plugins.
- Dependencies live in `.opencode/package.json` — OpenCode runs `bun install` at startup and rewrites the `@opencode-ai/plugin` pin to match its own runtime version. Committing the current pin is expected; the file may drift after a runtime upgrade. Do not manually downgrade — that fights the runtime and produces version-mismatch warnings.
- rldyour plugins (10):
  - `ry-bootstrap.ts` — `session.created` banner via `client.app.log`, `experimental.session.compacting` context push (MCP list read dynamically from `opencode.json` via `Bun.file()`), and `experimental.compaction.autocontinue` disables synthetic continue on overflow.
  - `ry-env-protection.ts` — `tool.execute.before` blocks read/bash of sensitive files (`.env*`, `.pem`, `.key`, etc.) with `.env.example` whitelist; surfaces rationale via `client.tui.showToast` before throwing.
  - `ry-shell-strategy.ts` — `shell.env` injects non-interactive git/CI env; `tool.execute.before` blocks `git push --force` without `--force-with-lease`, warns on destructive `rm`. Advice surfaces as toasts.
  - `ry-sync-reminder.ts` — `session.idle` ending-session toast + structured log.
  - `ry-flow-hooks.ts` — `tool.execute.after` Conventional Commits advice and post-commit `/ry-sync` nudge as toasts (sole owner of post-commit advice; ry-sync-reminder does not duplicate).
  - `ry-tools.ts` — registers 5 custom tools (`rldyour_validate_config`, `rldyour_check_deps`, `rldyour_lsp_health`, `rldyour_git_audit`, `rldyour_fullrepo_status`) via the `tool` plugin hook. Each wraps an existing diagnostic script so the LLM can drive checks without a bash round-trip.
  - `ry-command-audit.ts` — `command.execute.before` appends one credential-sanitized line per slash command invocation to `.serena/.command_audit.log` (runtime marker, never committed; 256 KiB rolling cap).
  - `ry-tool-hints.ts` — `tool.definition` appends a one-sentence routing hint to known MCP tool descriptions. Uses OpenCode v1.14.48 tool ID format `<server>_<tool>` (single underscore; dashes preserved).
  - `ry-permission-policy.ts` — `permission.ask` deny-only policy: blocks `git push --force` without `--force-with-lease`, catastrophic `rm -rf` targets, and `git push --no-verify` on product branches. Never auto-allows; preserves user consent on legitimate prompts.
  - `ry-system-context.ts` — `experimental.chat.system.transform` injects dynamic runtime context (today's date, current git branch, HEAD SHA, dirty-tree status) into every system prompt, grounding the LLM in "now" facts that AGENTS.md cannot carry.
- See `references/opencode-plugin-patterns.md` for the full hook surface, adopted patterns, and CLI extension points the marketplace can drive.

### Permissions
- Global permissions in `opencode.json` → `permission`.
- Per-agent overrides in `.opencode/agents/<name>.md` frontmatter.
- Values: `"allow"`, `"ask"`, `"deny"`, or object with glob patterns.
- Key permission keys: `read`, `edit`, `glob`, `grep`, `bash`, `task`, `webfetch`, `websearch`, `lsp`, `skill`, `question`, `external_directory`, `doom_loop`, `todowrite`.

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

MCP tools follow the OpenCode v1.14.48 `<server>_<tool>` naming pattern (single underscore separator; server names sanitised via `[a-zA-Z0-9_-]` allowlist, every other char replaced with `_`; dashes preserved). For example:
- Serena: `serena_find_symbol`, `serena_get_symbols_overview`, etc.
- Context7: `context7_resolve-library-id`, `context7_query-docs`
- DeepWiki: `deepwiki_*`
- Grep: `grep_searchGitHub`
- Chrome DevTools: `chrome-devtools_list_console_messages` (dash preserved)

Source: `packages/opencode/src/mcp/index.ts` build line `result[sanitize(clientName) + "_" + sanitize(mcpTool.name)]`. The legacy `mcp__server__tool` format from Claude Code does NOT match OpenCode's runtime.

## Engineering Rules

- Quality and correctness are higher priority than speed.
- No hacks, temporary workarounds, fake implementations, or swallowed errors.
- Keep systems synchronized across code, docs, configuration, git history, and Serena memories.
- Prefer low semantic entropy: reuse existing patterns, keep boundaries clear.
- Code is the source of truth. Memories and docs must reflect verified code.
- Use Sequential Thinking MCP for non-trivial decisions.
- Conventional Commits for all changes. Atomic commits per logical unit.
- Never commit secrets, runtime markers, browser artifacts, or local credentials.

## Don'ts

- Do NOT implement without passing context-sufficiency gate.
- Do NOT skip reviewer phase for security-sensitive or user-visible changes.
- Do NOT skip browser validation for UI changes without explicit reasoning.
- Do NOT force-push product branches (use --force-with-lease if necessary).
- Do NOT commit without Conventional Commits format.
- Do NOT deliver final task without running /ry-sync.
- Do NOT start `stdio` language servers manually; OpenCode manages lifecycle.
- Do NOT use `bunx`/`uvx` as runtime for long-lived LSP servers.
- Do NOT use `npx`; always use `bunx` for npm packages.
- Do NOT auto-edit `.serena/project.yml` without explicit user request.

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

## Serena Memories And Project Knowledge

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
- `fullrepo` is the standard branch for portable agent-only context. Normal branches should exclude agent-only files through `.git/info/exclude`.
- Agent-only files include: project-root `AGENTS.md`, `.serena/` knowledge, `.opencode/` agents/skills/commands/plugins, `.claude/`, `.cursor/rules/`, `.agents/`, and similar AI workflow directories.
- Use `scripts/fullrepo_sync.sh` for fullrepo branch management:
  - `bootstrap-init`: Install exclude patterns and restore from fullrepo.
  - `restore`: Restore agent-only files from origin/fullrepo.
  - `publish`: Publish current agent-only files to origin/fullrepo.
  - `status` / `status-json`: Check sync state.

## Validation Commands

- `scripts/validate_config.sh` — Validate opencode.json, skill / agent / command frontmatter, VERSION semver. Backed by `scripts/_validate_helpers.py`.
- `python3 -m pytest scripts/tests/` (or `uvx --from "pytest==9.0.2" pytest scripts/tests/`) — 259 cases across 9 suites (validate_helpers + extract_pins + skill_routing + command_audit_sanitizer + plugin_surface + opencode_resolve + permission_policy_regexes + smoke_mcp + validate_instruction_docs). Required green for release.
- `scripts/check_deps_freshness.sh` (with helper `scripts/_extract_pins.py`) — List pinned MCP dependencies (`--json` mode for automation).
- `scripts/smoke_mcp_capabilities.py` — Probe every declared MCP server for reachability (remote HEAD-then-GET; local 3 s spawn window). `--json` mode for automation.
- `scripts/validate_instruction_docs.py` — Verify `AGENTS.md` and `.claude/CLAUDE.md` exist, exceed size threshold, and contain required anchor headings.
- `scripts/collect_diagnostics.sh` — Timestamped local diagnostic bundle under `diagnostics/` (git-ignored). Use `--include-doctor` to add LSP and opencode doctor passes.
- `scripts/bootstrap_opencode.sh` — Bootstrap project structure and exclude patterns.
- `scripts/doctor_opencode.sh` — Check dependencies and configuration health.
- `scripts/check_lsps.sh` — Check LSP server commands and project prerequisites.
- `scripts/install_lsps.sh` — Brew-first LSP server installation.
- `scripts/flow_post_task_state.sh` — Compute git/Serena/fullrepo/instruction-docs state as JSON.
- `scripts/git_sync_audit.sh` — Audit git state: branch, upstream, dirty files, worktrees.
- `scripts/deploy_readiness.sh` — Check deploy readiness for a target server.
- `scripts/detect_project_checks.sh` — Auto-detect project-native test/lint/typecheck commands.
- `scripts/fullrepo_sync.sh status` — Check git and fullrepo sync state.
- Native: `opencode debug config | agent <name> | skill | info | startup` — authoritative resolved state.
- See `docs/observability.md` for the full triage flow.

## Done Criteria

- `opencode.json` is valid JSON with correct schema.
- All agent and skill files have required frontmatter fields.
- Skill names are valid (1-64 chars, kebab-case, matching directory name).
- Agent descriptions are present and specific (1-1024 chars).
- `git status` is clean of non-agent files.
- Serena memories reflect current code state.
- Conventional commits for source/docs/Serena knowledge are separate when it improves history clarity.
- No secrets in agent-only files (checked by fullrepo_sync.sh publish).