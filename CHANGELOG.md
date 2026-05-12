# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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