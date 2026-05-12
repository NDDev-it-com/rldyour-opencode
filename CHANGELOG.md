# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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