# CORE_03 Plugins, Agents, and Commands

Verified facts at HEAD 1f1510b.
Sources: `.opencode/plugins/*.ts`, `.opencode/agents/*.md`, `.opencode/commands/*.md` (all verified by direct file read).

Last commit: 1f1510b

## Plugins (10)

Location: `.opencode/plugins/` — auto-discovered by OpenCode at startup. Not registered in `opencode.json` (plugin field is `[]`).
Dependency: `.opencode/package.json` → `@opencode-ai/plugin: 1.14.48` (dependencies, auto-pinned by OpenCode at startup via bun install).

Source: `AGENTS.md` L132, file reads of each `.ts`. All 10 plugins verified by `test_plugin_surface.py` EXPECTED_PLUGINS set (lines 20-31).

All plugins use `client.app.log` (structured server-side logging) and `client.tui.showToast` (user-visible TUI banner) where applicable. `console.log` is absent from all plugin files at HEAD (enforced by `test_plugin_surface.py::test_no_console_log_in_plugin_production_code`, 0.10.1).

### ry-bootstrap.ts

- Hook: `event` (session.created) — logs session start banner with project name and workflow hint via `client.app.log`.
- Hook: `experimental.session.compacting` — pushes context block into `output.context` with project name, dir, workflow sequence, MCP server list read dynamically from `opencode.json` at compaction time via `Bun.file().text()` + `JSON.parse` (filters `enabled !== false`, sorts alphabetically). On read failure logs a warn before falling back to neutral hint. Reviewer subagent list stays inline (stable). Communication rule and quality rules also pushed.
- Hook: `experimental.compaction.autocontinue` — disables autocontinue for sessions that hit context overflow (logs info via `client.app.log`).
- Bun runtime globals used: `Bun.file()` (no `node:fs/promises` import — avoids missing `@types/node`).
- Plugin factory destructures `({ project, directory })`. `project` typed via local cast `proj as { name?, path? }`.

### ry-env-protection.ts

- Hook: `tool.execute.before` — intercepts bash/read tool calls, checks file path against blocked patterns, throws if sensitive. Toast shown via `client.tui.showToast` BEFORE throwing (user-visible block reason).
- Blocked patterns: `.env$`, `.env.`, `credentials`, `/.ssh/`, `/.gnupg/`, `/.aws/`, `secret`, `private[_-]?key`, `service[_-]?account`, `.pem$`, `.p12$`, `.pfx$`, `.key$`
- Allowlist: `.env.example`, `.env.template`, `.env.sample`

### ry-shell-strategy.ts

- Hook: `shell.env` — injects `GIT_TERMINAL_PROMPT=0`, `CI=1`, `NODE_OPTIONS=--max-old-space-size=4096` into every shell environment.
- Hook: `tool.execute.before` — three guards:
  1. `git push` (without `--no-verify`): logs quality checklist.
  2. `git push --force` / `-f` without `--force-with-lease`: throws `Error("[rldyour] Blocked git push --force / -f without --force-with-lease (data-loss risk).")`.
  3. `rm -rf .../` on non-node_modules path: logs destructive warning.
- **Flag-boundary regex (0.10.1 fix)**: `\b--force\b` was silently broken (word boundary cannot assert between space and dash). Now uses `FLAG_BOUNDARY_PRE = "(?<![A-Za-z0-9-])"` + `FLAG_BOUNDARY_POST = "(?![A-Za-z0-9-])"` pairs with `/i` flag. `--force` matches; `--force-with-lease` correctly excluded. Source: `.opencode/plugins/ry-shell-strategy.ts` lines 53-57.

### ry-flow-hooks.ts

- Hook: `tool.execute.after` — monitors bash tool output. Dead `headBefore` variable removed at HEAD.
  1. `git commit` without conventional-commit format in result: logs format advice via `client.app.log`.
  2. `git commit|merge|cherry-pick|rebase` (non-amend) with "changed" in output: logs `/ry-sync` suggestion.

### ry-sync-reminder.ts

- Hook: `event` (session.idle) — shows sync checklist banner via `client.tui.showToast`.
- Hook: `tool.execute.after` — on `git commit`: checks first output line against conventional commit pattern, logs format suggestion if non-conforming via `client.app.log`.

### ry-tools.ts

- Hook: `tool` — registers 5 custom diagnostic tools (multi-domain aggregator; bundles intentional per file header comment).
- Tool IDs and scripts:
  - `rldyour_validate_config` → `bash scripts/validate_config.sh`
  - `rldyour_check_deps` → `bash scripts/check_deps_freshness.sh --json`
  - `rldyour_lsp_health` → `bash scripts/check_lsps.sh`
  - `rldyour_git_audit` → `bash scripts/git_sync_audit.sh`
  - `rldyour_fullrepo_status` → `bash scripts/fullrepo_sync.sh status-json`
- Each tool: `args: {}` (no user input), stamps `ctx.metadata({ title, metadata: { exitCode } })` for TUI pass/fail display.
- Dispatch path for `tool.definition` hook verified by `test_plugin_surface.py::test_ry_tool_hints_dispatch_path_wired` (0.10.1).

### ry-command-audit.ts

- Hook: `command.execute.before` — appends one credential-sanitized line per slash-command invocation to `.serena/.command_audit.log` (runtime marker; never committed; 256 KiB rolling cap with reset).
- `sanitizeArgs()` redacts: `sk-*` OpenAI/Anthropic keys, `ghp_`/`ghs_`/`gho_` GitHub tokens, `glpat-*` GitLab PATs, `AKIA`/`ASIA` AWS keys, `xox[abprs]-*` Slack tokens, `eyJ...` JWTs, PEM blocks, and any 32+ char alphanumeric/underscore/hyphen run (fallback). Sanitize runs on full raw args string BEFORE the 280-char slice (sanitize-before-slice order). Warn path uses `client.app.log`.
- Concurrency note: read-modify-write is non-atomic but serialised by the single Bun event loop within one process.

### ry-tool-hints.ts

- Hook: `tool.definition` — appends a one-sentence routing hint to known MCP tool descriptions.
- HINTS keys use OpenCode v1.14.48 `server_tool` format (NOT legacy `mcp__server__tool` Claude Code format — that format is dead code in OpenCode). Source: `packages/opencode/src/mcp/index.ts` `sanitize(serverName) + "_" + sanitize(toolName)`.
- 14 HINTS keys (verified by `test_plugin_surface.py` test_hints_use_opencode_tool_id_format): `serena_find_symbol`, `serena_get_symbols_overview`, `serena_find_referencing_symbols`, `serena_search_for_pattern`, `serena_read_memory`, `playwright_browser_navigate`, `chrome-devtools_list_console_messages`, `chrome-devtools_performance_start_trace`, `context7_resolve-library-id`, `context7_query-docs`, `deepwiki_ask_question`, `grep_searchGitHub`, `semgrep_semgrep_scan`, `sequential-thinking_sequentialthinking`.
- All keys reference real `opencode.json.mcp` server keys. Legacy alias `mcp__context7__get-library-docs` is blacklisted and cannot be reintroduced. Entire `mcp__` prefix is blocked by `test_plugin_surface.py` line 98.

### ry-permission-policy.ts (added in 0.10.0)

- Hook: `permission.ask` — deny-only policy. Fires only when the static permission config sets a slot to `"ask"`. Blocks categorically dangerous patterns before the user prompt appears.
- IMPORTANT: this plugin only DENIES. It never auto-allows. User interactive consent on legitimate `"ask"` prompts is preserved verbatim.
- Uses `client.app.log` for logging and `client.tui.showToast` for user-visible error toasts.
- **Flag-boundary regex (0.10.1 fix)**: same `FLAG_BOUNDARY_PRE`/`FLAG_BOUNDARY_POST` pair as `ry-shell-strategy.ts`. Source: `.opencode/plugins/ry-permission-policy.ts` lines 69-73. Also fixed: product-branch alternation from `\bmain|master|release|production\b` → `\b(main|master|release|production)\b` to prevent false-positive denials on `mainline`/`mainframe`/`productionish`. Added `-f` short form via `(?:^|\s)-f(?:\s|$)`.
- Source: SDK Permission shape in `dist/gen/types.gen.d.ts`; hook contract in `@opencode-ai/plugin` `dist/index.d.ts` ("permission.ask").

### ry-system-context.ts (added in 0.10.0)

- Hook: `experimental.chat.system.transform` — injects dynamic context (today's date, current git branch, recent git activity) into the system prompt on every chat completion.
- **Factory-init caching (0.10.1)**: `branch` and `headShort` are cached once at plugin factory init (via `git rev-parse --abbrev-ref HEAD` and `git rev-parse --short=7 HEAD`). The per-turn hook only spawns `git status --porcelain` to detect dirty/clean state. Saves 2 subprocess spawns per chat completion turn × N turns per session. Source: `.opencode/plugins/ry-system-context.ts` lines 43-50.
- Runtime line format (unchanged): `[rldyour runtime] date=YYYY-MM-DD branch=<branch> head=<short> worktree=<dirty|clean>`. Fallback value `"unknown"` on git failure. Verified by `test_plugin_surface.py::test_ry_system_context_injects_runtime_fields` (0.10.1).
- Uses `Bun.spawn` with short timeouts and silent fallbacks so transient failures cannot block the model call.
- Uses `client.app.log` for logging injected facts.

## Agents (9)

Location: `.opencode/agents/*.md` — single source of truth. Not duplicated in opencode.json.

| File | mode | model | steps | color | hidden | edit | task | external_directory |
|---|---|---|---|---|---|---|---|---|
| customize-opencode.md | subagent | (inherits) | 36 | accent | — | allow | — | — |
| flow-architecture-review.md | subagent | (inherits) | 36 | #3b82f6 | true | deny | ask | deny |
| flow-consistency-review.md | subagent | (inherits) | 36 | #a855f7 | true | deny | ask | deny |
| flow-integration-review.md | subagent | (inherits) | 36 | warning | true | deny | ask | deny |
| flow-memory-sync.md | subagent | (inherits) | 36 | #eab308 | true | allow | deny | deny |
| flow-quality-review.md | subagent | (inherits) | 36 | success | true | deny | ask | deny |
| flow-security-review.md | subagent | (inherits) | 42 | error | true | deny | ask | deny |
| flow-verification-review.md | subagent | (inherits) | 36 | #ec4899 | true | deny | ask | deny |
| ry-explore.md | subagent | (inherits) | 90 | info | — | deny | deny | deny |

Note: OpenCode v1.14 schema requires `color` to match `^#[0-9a-fA-F]{6}$` (hex) or one of the enum values `primary|secondary|accent|success|warning|error|info`. Named CSS colors are not valid.

Notes:
- `task` + `external_directory` permissions added in 0.10.0 as defense for OpenCode v1.14.31 + v1.14.46 subagent inheritance fixes.
- All reviewer subagents (flow-*-review) use `hidden: true`, `edit: deny`, `bash: { "*": ask, "git diff": allow, "git log*": allow, "git show*": allow }`, `task: ask`, `external_directory: deny`.
- `flow-security-review` has `steps: 42` (others 36); includes `webfetch/websearch: allow` and `glob/grep/read: allow`.
- `flow-memory-sync` is the only review-track subagent with `edit: allow` — controls `.serena/memories/` writes. `task: deny`, `external_directory: deny`.
- No agent has a hardcoded model override — all inherit the top-level `model` (currently `opencode-go/glm-5.1`). Agent blocks only set `mode`, `permission`, `temperature`, `steps`, `hidden`, `color`.
- `customize-opencode` has `bash` allowlist: `cat *`, `node -e *`, `npx *`, `python3 *`, `jq *`.

## Commands (10)

Location: `.opencode/commands/*.md` — single source of truth. Not duplicated in opencode.json.

Bilingual descriptions added to 6 commands in 0.10.0 (`ry-deploy`, `ry-init`, `ry-newp`, `ry-review`, `ry-start`, `ry-sync`) — Russian-leading + English-trailing convention matching skills.

| File | agent | subtask |
|---|---|---|
| ry-deploy.md | build | — |
| ry-design.md | build | — |
| ry-explore.md | ry-explore | true |
| ry-init.md | build | — |
| ry-newp.md | build | — |
| ry-review.md | plan | — |
| ry-rules-review.md | plan | — |
| ry-sec-review.md | plan | — |
| ry-start.md | build | — |
| ry-sync.md | build | — |

Notes:
- `ry-explore` is the only command with `subtask: true` (forces subagent invocation).
- `ry-review`, `ry-rules-review`, `ry-sec-review` use `agent: plan` (read-heavy, edit/bash=ask).
- All others use `agent: build` (full permissions).
- Command bodies support `$ARGUMENTS`, `$1`/`$2`/..., `!`command`` (shell output), `@file` (file refs).
- Bilingual description format: Russian sentence first, English description after. Matches skill auto-routing convention verified by `test_skill_routing.py`.

## Domain Boundaries

Source: `AGENTS.md` L27-49

| Domain | Skills | Agents | Commands |
|---|---|---|---|
| Flow | flow-post-task-sync, ry-init, ry-start, ry-review, ry-newp, ry-deploy | flow-*review, flow-memory-sync | ry-init, ry-start, ry-review, ry-newp, ry-deploy, ry-sync |
| Serena (MCP) | serena-code-workflow, serena-memory-sync, serena-lsp-integration | — | — |
| Rules | quality-first-engineering, architecture-boundaries, implementation-discipline, dependency-compatibility-policy, verification-quality-gates, project-instructions-policy, ry-rules-review | — | — |
| Explore | tech-research, web-research | ry-explore | — |
| Browser | browser-tool-routing, browser-validation, browser-debug | — | — |
| Design | ry-design, figma-to-code, design-system-implementation, fsd-frontend-architecture, design-validation | — | — |
| Security | owasp-top-10-implementation, ry-sec-review | — | — |
| LSP | lsp-routing, lsp-health-check, lsp-setup | — | — |
| Docs sync | instruction-docs-sync | — | — |
| Config | — | customize-opencode | — |

Cross-domain rules:
- Only Serena domain invokes `mcp__serena__*`
- Only Browser domain invokes Playwright/Chrome-DevTools MCP
- Only Security domain invokes Semgrep MCP
- Flow domain orchestrates others via skills and subagents
- `ry-tools.ts` is the only multi-domain plugin; explicit comment in file header declares this bundling intent. Do not silently add a fourth-domain tool there without updating AGENTS.md and CHANGELOG.
