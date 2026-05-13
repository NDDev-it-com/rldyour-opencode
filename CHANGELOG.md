# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.1] - 2026-05-13

Hardening pass closing every defer item flagged by the 0.9.0 reviewer round, plus the previously-external decision to ship a real Claude Code project memory file.

### Added

- `.claude/CLAUDE.md` — Claude Code project memory written as a self-contained guide (not a thin pointer to AGENTS.md per `project-instructions-policy` anti-pattern). Tells a Claude-Code-resident developer that this repo is an OpenCode marketplace, where canonical knowledge lives, what NOT to do (treat OpenCode skills/agents/commands as Claude Code primitives), which validation gates apply, and how to reach AGENTS.md, references, decisions.
- `scripts/tests/test_plugin_surface.py` (6 cases) — defensive checks that catch regressions: plugin set on disk equals AGENTS.md count; `ry-tools` registers exactly the 5 advertised tool IDs; `ry-tool-hints` HINTS keys reference real `opencode.json.mcp` server keys; legacy `mcp__context7__get-library-docs` alias cannot be re-introduced; dead `project as { path? }` cast cannot reappear in any plugin.
- `scripts/tests/test_opencode_resolve.py` (4 cases, skipped when `opencode` CLI absent) — end-to-end integration: `opencode debug config` resolves cleanly; `opencode debug info` lists all 8 plugins; resolved skill count equals directory count; every `.opencode/agents/*.md` resolves under `opencode debug agent`. Catches schema-validation regressions that pass static checks but fail live OpenCode.
- Inline concurrency + sanitize-order notes in `ry-command-audit.ts` documenting the deliberate non-atomic read-modify-write (single Bun event loop serialises within process) and the deliberate sanitize-before-slice order (guarantees no credential reaches the log regardless of position).

### Changed

- `.github/workflows/validate.yml` — `actions/checkout@v4` and `actions/setup-python@v5` pinned to commit SHA (`34e114876b0b11c390a56381ad16ebd13914f8d5` and `a26af69be951a213d495a4c3e4e4022e16d87065` respectively). Defends CI against tag-hijack on the action repositories. Verified via `gh api repos/actions/<name>/git/refs/tags/<tag>`.

### Test coverage

- Total pytest cases: **194** (was 184). Breakdown: 27 validate_helpers + 12 extract_pins + 129 skill_routing + 16 command_audit_sanitizer + 6 plugin_surface + 4 opencode_resolve.

## [0.9.0] - 2026-05-13

OpenCode plugin-surface expansion. Adopt three previously-unused hook types so the marketplace exercises the full v1.14.48 plugin API instead of just session/tool/shell observation.

### Added

- **`.opencode/plugins/ry-tools.ts`** — 5 custom tools registered via the `tool` plugin hook so the LLM can drive diagnostic scripts directly:
  - `rldyour_validate_config` — runs `bash scripts/validate_config.sh`.
  - `rldyour_check_deps` — runs `bash scripts/check_deps_freshness.sh --json`.
  - `rldyour_lsp_health` — runs `bash scripts/check_lsps.sh`.
  - `rldyour_git_audit` — runs `bash scripts/git_sync_audit.sh`.
  - `rldyour_fullrepo_status` — runs `bash scripts/fullrepo_sync.sh status-json`.
  Each tool stamps `ctx.metadata({ title, metadata: { exitCode } })` so the TUI shows pass/fail at a glance.
- **`.opencode/plugins/ry-command-audit.ts`** — `command.execute.before` plugin appends one credential-sanitized line per slash command invocation to `.serena/.command_audit.log` (runtime marker; never committed; 256 KiB rolling cap with reset).
- **`.opencode/plugins/ry-tool-hints.ts`** — `tool.definition` plugin appends a one-sentence routing hint to known MCP tool descriptions (Serena `find_symbol`, Chrome DevTools console, Context7 docs, Semgrep scan, Sequential Thinking, etc.). Encodes the AGENTS.md tool-priority matrix inline to the LLM.
- **`scripts/tests/test_skill_routing.py`** — 129 parametrized pytest cases (32 skills × 4 routing checks + 1 uniqueness): description length 80-1024, presence of Russian routing phrase (`Используй для` / `Use for`), presence of English routing block (`EN triggers:` or English-leading head), skill name kebab-case. Borrowed from codex marketplace's deterministic-routing-policy pattern, adapted to OpenCode's description-based auto-routing.
- **`references/opencode-plugin-patterns.md`** — full reference for the `@opencode-ai/plugin` v1.14.48 hook surface (server-side + TUI), patterns adopted in this repo, explicit list of unused-but-known hooks, and CLI extension points the marketplace can drive (`opencode run / debug / serve / web / acp / github / pr / stats / export / import`).

### Changed

- Skill descriptions for `flow-post-task-sync`, `instruction-docs-sync`, `ry-deploy`, `ry-init`, `ry-newp`, `ry-review`, `ry-start` extended with explicit `Используй для:` (RU triggers) and `EN triggers:` (EN keyword block) so OpenCode auto-routing matches both languages reliably. Verified by the new `test_skill_routing.py` suite.
- AGENTS.md Plugins section now documents all 8 plugins with exact hook subscriptions and links to `references/opencode-plugin-patterns.md`.
- README catalog tables updated: 8 plugins (was 5), 16 reference docs (was 15), 3 pytest suites with 168 cases (was 1 with 27).

## [0.8.1] - 2026-05-13

Post-0.8.0 hardening based on parallel reviewer findings (architecture / quality / consistency / integration / verification / security tracks).

### Added

- `scripts/tests/test_validate_helpers.py` (27 cases) and `scripts/tests/test_extract_pins.py` (12 cases) — full pytest coverage of the validator and pin extractor. Run via `python3 -m pytest scripts/tests/` or `uvx --from "pytest==9.0.2" pytest scripts/tests/`.
- `scripts/tests/__init__.py` and `scripts/tests/conftest.py` — package marker and pytest session config (adds `scripts/` to `sys.path`). Removes the previous inline `sys.path.insert` hack from the test module body.
- `scripts/check_deps_freshness.sh` + `scripts/_extract_pins.py` — list every pinned MCP dependency in `opencode.json` (npm via bunx, PyPI via uvx, Dart SDK). `--json` mode emits a documented JSON envelope (`{pins: [{kind,server,name,version}], count}`).
- `DuplicateYamlKey` exception in `_validate_helpers.py` — rejects skill/agent/command frontmatter that contains the same top-level key twice (regex YAML parser previously kept the first match silently).
- `.github/workflows/validate.yml` — Python 3.13 setup + pinned `pytest==9.0.2` install + pytest run. CI and local validation now exercise the same surface.
- `docs/decisions/*.md` — architecture decision archive (4 files moved from former `thinking/` directory in commit `159fd99`).
- AGENTS.md Source Of Truth gains a `docs/decisions/*.md` entry; Validation Commands gains pytest, check_deps_freshness, and `opencode debug *` rows.
- README Validation block lists pytest + check_deps_freshness; Catalog has new rows for `docs/decisions/` and `scripts/tests/`.

### Changed

- `_validate_helpers.py`: `_yaml_top_key` now (a) supports YAML block scalars (`description: |`), (b) reads `utf-8-sig` so files with UTF-8 BOM parse correctly, (c) anchors trailing whitespace as `[^\S\n]*` so an empty inline scalar no longer captures the next line's text.
- `_validate_helpers.py`: SSoT command-block gate added — rejects an `opencode.json` that defines a `command` block (commands must live in `.opencode/commands/*.md`).
- `scripts/validate_config.sh`: rewritten without inline zsh-heredoc Python; delegates to `_validate_helpers.py`. Adds `log_warn` / `log_info` helpers consistent with other scripts.
- `scripts/fullrepo_sync.sh`: `AGENT_ONLY_PATTERNS` updated `thinking/` → `docs/` (matches actual layout after the `159fd99` rename). Secret detector warning now uses `cut -d: -f1` (was `cut -d: -1`, a no-op flag that suppressed the file path in the warning).
- `scripts/check_deps_freshness.sh`: `--json` path writes directly to stdout (no `mktemp` temp file, no trap risk).
- `scripts/_extract_pins.py`: `UV_FROM_RE` accepts PyPI names containing `.` (e.g. `zope.interface`); module docstring documents the full JSON envelope contract.
- AGENTS.md Plugins section rewritten against `.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts` v1.14.48: removed non-existent `permission.asked`/`permission.replied`/`tui.*` server hooks; added `config`, `chat.message`, `chat.params`, `chat.headers`, `command.execute.before`, `tool.definition`, `auth`, `provider`, four `experimental.*`.
- `.opencode/plugins/ry-bootstrap.ts`: MCP list pushed into compaction context is read dynamically from `opencode.json` via `Bun.file()` instead of being hardcoded. Catch path logs a warning before falling back to neutral hint.
- `.opencode/plugins/ry-sync-reminder.ts`: removed duplicate `tool.execute.after` handler — Conventional Commits advice owned exclusively by `ry-flow-hooks.ts`.
- `.opencode/agents/customize-opencode.md`: body forbids adding `command` block to `opencode.json`; color schema constraint documented; new-agent flow uses `opencode debug agent <name>`.
- `.github/workflows/validate.yml`: CI delegates to `bash scripts/validate_config.sh` instead of inline Python/bash checks (eliminates CI-vs-local schema drift).
- README placeholder env vars renamed `your-key` → `YOUR_PLACEHOLDER_KEY` so the `fullrepo_sync.sh publish` secret detector whitelist correctly ignores them.

### Removed

- `.claude/CLAUDE.md`: Claude Code project-memory thin pointer (anti-pattern called out by `project-instructions-policy` skill; AGENTS.md cross-tool standard covers Claude Code without a separate memory file).

### Fixed

- Model IDs in `opencode.json` and `.opencode/agents/*.md` migrated to OpenCode v1.14.48 registry-valid IDs (`claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-opus-4-7`). Previous IDs caused `config.providers` / `provider.list` / `app.agents` / `config.get` `ConfigInvalidError`.
- Agent `color` frontmatter migrated from named CSS colors to hex / enum per schema. Prior values (`blue`, `yellow`, `purple`, …) were rejected by OpenCode v1.14.
- `_validate_helpers.py` correctly handles `description: |` block scalars and UTF-8 BOM; empty inline `description:` no longer silently slurps the next line.

## [0.8.0] - 2026-05-13

Validated against OpenCode v1.14.48 (`opencode debug config` resolves cleanly).

### Added

- **`docs/`**: marketplace operator guides — `release-process.md`, `dependency-updates.md`, `rollback-restore.md`.
- **`scripts/_validate_helpers.py`**: Python module backing the rewritten `scripts/validate_config.sh`. Validates `opencode.json` shape, skill name/description, agent frontmatter (description + mode + color enum or hex), command frontmatter, VERSION semver. Supports YAML block scalars (`description: |`) and UTF-8 BOM. Single source of truth gate: rejects `command` block in `opencode.json` (commands must live in `.opencode/commands/*.md`).
- AGENTS.md skill spec: explicit allowed optional frontmatter (`license`, `compatibility`, `metadata`) and explicit forbidden Claude-Code/Codex residue fields.
- AGENTS.md plugin event list expanded to match OpenCode v1.14 actual surface.
- AGENTS.md agent spec: explicit `color` schema constraint (hex `^#[0-9a-fA-F]{6}$` or enum `primary|secondary|accent|success|warning|error|info`).
- README catalog tables for Models, MCP servers, reviewer subagents (with schema-valid colors), validation commands.

### Changed

- **`.opencode/plugins/ry-bootstrap.ts`**: MCP list pushed into compaction context is now read dynamically from `opencode.json` via `Bun.file()` instead of being hardcoded. Catch path now logs a warning before falling back.
- **`.opencode/plugins/ry-sync-reminder.ts`**: removed duplicate `tool.execute.after` handler — Conventional Commits advice is owned exclusively by `ry-flow-hooks.ts`.
- **`.opencode/agents/customize-opencode.md`**: body forbids adding `command` block to `opencode.json` (single source of truth); color schema constraint documented; new-agent flow uses `opencode debug agent <name>` for verification.
- **`.github/workflows/validate.yml`**: CI now delegates to `bash scripts/validate_config.sh` instead of inline Python/bash checks, keeping CI and local validators identical.
- **`scripts/validate_config.sh`**: rewritten without zsh-heredoc Python (delegates to `_validate_helpers.py`). Added `log_warn` / `log_info` helpers consistent with other scripts.
- `docs/dependency-updates.md`: removed dangling "track via TODO in CHANGELOG" cross-reference.

### Removed

- **`.claude/CLAUDE.md`**: Claude Code project-memory pointer file. This is an OpenCode-native marketplace and the AGENTS.md cross-tool standard (https://agents.md/) already covers any Claude Code use case. The previous thin-pointer file matched the anti-pattern called out in `project-instructions-policy` skill.

### Fixed

- Model IDs in `opencode.json` and all `.opencode/agents/*.md` use OpenCode v1.14.48 registry-valid identifiers (`claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-opus-4-7`). Prior IDs (`claude-sonnet-4-20250514`, `claude-haiku-4-20250514`, `claude-opus-4-20250514`) caused `config.providers` / `provider.list` / `app.agents` / `config.get` `ConfigInvalidError`.
- Agent `color` frontmatter migrated from named CSS colors to hex / enum per schema. Prior values (`blue`, `yellow`, `purple`, `orange`, `green`, `red`, `pink`, `cyan`) were rejected by OpenCode v1.14 (only hex `^#[0-9a-fA-F]{6}$` or enum `primary|secondary|accent|success|warning|error|info` accepted).
- `_validate_helpers.py` handles `description: |` block scalars correctly; previously returned the literal `|` and skipped the length check.
- `_validate_helpers.py` uses `utf-8-sig` encoding so files with UTF-8 BOM do not produce spurious `missing frontmatter delimiter` errors.

## [0.7.0] - 2026-05-12

### Added

- **4 missing commands**: ry-design, ry-explore, ry-sec-review, ry-rules-review (matching reference implementations).
- **LSP utility scripts**: check_lsps.sh (health check for 17+ language servers) and install_lsps.sh (brew-first installation).
- **Flow utility scripts**: flow_post_task_state.sh (JSON state computation), git_sync_audit.sh, deploy_readiness.sh, detect_project_checks.sh.
- **New plugin**: ry-flow-hooks.ts (post-tool commit advice and auto-sync nudge).
- AGENTS.md updated with validation commands section listing all 9 scripts.

### Changed

- Commands now use OpenCode-specific features: `subtask: true` for ry-explore, correct MCP tool names (`mcp__figma__*` not `mcp__plugin_rldyour-mcps_figma__*`).
- All 10 commands now present (6 original + 4 new), matching reference implementation coverage.

## [0.6.0] - 2026-05-12

### Added

- **Fullrepo sync script** (`scripts/fullrepo_sync.sh`): bootstrap-init, restore, publish, status, status-json — full agent-only file branch management.
- `.env.example` documenting required environment variables (CONTEXT7_API_KEY, GITHUB_PERSONAL_ACCESS_TOKEN).
- Domain boundaries section in AGENTS.md mapping each skill/agent/command to its owning domain.
- Don'ts section in AGENTS.md with 10 explicit prohibitions.
- Validation commands section in AGENTS.md documenting all scripts.
- `.git/info/exclude` pattern management documented in Git and Sync section.
- Updated MCP servers table: dart-flutter now enabled, figma URL corrected to `/mcp`.

### Changed

- **Single source of truth for agents and commands**: removed all subagent and command definitions from `opencode.json` — they live exclusively in `.opencode/agents/*.md` and `.opencode/commands/*.md`.
- **MCP timeouts reduced**: 30s for local servers, 15s for remote (was 90s/60s).
- **AGENTS.md major rewrite**: added domain boundaries, don'ts, validation commands, fullrepo sync docs, plugin event reference.
- **Plugins enhanced**: ry-bootstrap.ts now includes MCP server list and reviewer subagent list in compaction context; ry-env-protection.ts has improved pattern matching with .env.example whitelist; ry-shell-strategy.ts adds --force-with-lease guard and destructive rm warning; ry-sync-reminder.ts adds conventional commit format advice on commit events.

## [0.5.0] - 2026-05-12

### Changed

- **Breaking: single source of truth for agents and commands.**
  - Removed 8 subagent definitions from `opencode.json` — they live only in `.opencode/agents/*.md`.
  - Removed 6 command definitions from `opencode.json` — they live only in `.opencode/commands/*.md`.
  - `opencode.json` now only contains `build` and `plan` primary agent overrides (permissions).
- Reduced MCP timeout values: 30s for local servers, 15s for remote (was 90s/60s).
- Updated AGENTS.md to document single-source-of-truth convention explicitly.

## [0.4.0] - 2026-05-12

### Changed

- LSP configuration changed from `"lsp": true` to `"lsp": {}` (object = built-ins enabled + custom overrides).
- Added 8 custom LSP servers to cover all languages from reference implementations:
  - `ruff` (Python linter companion to pyright)
  - `vscode-html` (HTML)
  - `vscode-css` (CSS/SCSS/SASS/Less)
  - `vscode-json` (JSON/JSONC)
  - `docker` (Dockerfile)
  - `taplo` (TOML)
  - `marksman` (Markdown)
  - `qmlls` (Qt QML, optional)
- Total LSP coverage: 35+ built-in + 8 custom = 43+ language servers.
- AGENTS.md LSP section expanded with runtime rules and custom server table.

## [0.3.0] - 2026-05-12

### Changed

- MCP configuration: complete rewrite from scratch based on both reference implementations.
- Replaced `npx -y` with `bunx` for all npm-based MCP servers (serena, sequential-thinking, playwright, chrome-devtools, context7, shadcn).
- Fixed serena: changed from `@anthropic/serena-mcp` to `serena-agent==1.3.0` via `uvx` with correct flags.
- Fixed sequential-thinking: version `0.7.0` → `2025.12.18`, added `DISABLE_THOUGHT_LOGGING` env var.
- Fixed playwright: added `--headless` and `--caps=network,storage,testing,devtools` flags.
- Fixed figma URL: `/` → `/mcp`.
- Added `timeout` values: 90000ms for local servers, 60000ms for remote servers.
- Added 5 missing MCP servers: chrome-devtools, semgrep, shadcn, dart-flutter, openai-docs.
- Total MCP servers: 13 (8 local, 5 remote; dart-flutter disabled by default).

## [0.2.0] - 2026-05-12

### Added

- OpenCode plugin system with 4 event-driven plugins replacing advisory lifecycle hooks.
- `ry-bootstrap.ts`: session.created context injection and compaction context preservation.
- `ry-env-protection.ts`: tool.execute.before read/bash blocking for sensitive file paths.
- `ry-shell-strategy.ts`: shell.env non-interactive git env injection and pre-push advisory.
- `ry-sync-reminder.ts`: session.idle reminder to run /ry-sync before ending session.
- `.opencode/package.json` for plugin TypeScript dependencies.
- `opencode.json` plugin section (empty array for future npm plugins).
- AGENTS.md updated with Plugins section documenting events, structure, and rldyour plugins.

## [0.1.0] - 2026-05-12

### Added

- Initial rldyour-opencode marketplace with full OpenCode configuration.
- `opencode.json` master config with providers, MCP servers, LSP, agents, permissions, commands.
- 9 subagent definitions for review, memory sync, and deep research workflows.
- 32 skill definitions covering flow, Serena, rules, explore, browser, design, security, and LSP domains.
- 6 slash commands for SDLC workflow (ry-init, ry-start, ry-review, ry-newp, ry-deploy, ry-sync).
- 16 reference documents for skills and agents.
- Bootstrap, validation, and diagnostics scripts.
- AGENTS.md cross-tool root instructions adapted for OpenCode format.
- Serena project configuration and initial memory structure.
- 7 MCP servers configured (serena, sequential-thinking, playwright, context7, deepwiki, grep, github, figma).
- Built-in LSP support enabled for 30+ languages.
- Reviewer subagents with per-agent permissions (read-only, bash allowlisted for git commands).