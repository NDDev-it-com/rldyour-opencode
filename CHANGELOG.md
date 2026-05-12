# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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