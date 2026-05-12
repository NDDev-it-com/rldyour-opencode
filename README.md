# rldyour-opencode

Personal OpenCode configuration marketplace by `rldyourmnd`. Russian-first SDLC workflow, Serena integration, MCP transport, code review, design, security, LSP, and engineering rules — all adapted for the OpenCode AI coding agent format.

## What This Is

A self-contained OpenCode project configuration that provides:

- **32 skills** for automatic workflow routing (SDLC, Serena, research, browser, design, security, LSP, rules)
- **9 subagents** for specialized tasks (6 reviewer tracks, memory sync, deep research)
- **6 slash commands** for lifecycle orchestration (`/ry-init`, `/ry-start`, `/ry-review`, `/ry-newp`, `/ry-deploy`, `/ry-sync`)
- **7 MCP servers** pre-configured (Serena, Sequential Thinking, Playwright, Context7, DeepWiki, Grep, GitHub)
- **Full LSP support** via OpenCode's built-in 30+ language servers
- **Granular permissions** per agent (reviewers are read-only, bash allowlisted for git)

## Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/rldyourmnd/rldyour-opencode.git
   cd rldyour-opencode
   ```

2. Copy the configuration into your project:
   ```bash
   cp opencode.json /path/to/your/project/opencode.json
   cp -r .opencode /path/to/your/project/.opencode
   cp AGENTS.md /path/to/your/project/AGENTS.md
   ```

3. Set up API keys:
   ```bash
   export ANTHROPIC_API_KEY=your-key
   export CONTEXT7_API_KEY=your-key      # optional, for Context7
   export GITHUB_PERSONAL_ACCESS_TOKEN=your-token  # optional, for GitHub MCP
   ```

4. Run OpenCode in your project:
   ```bash
   cd /path/to/your/project
   opencode
   ```

5. Initialize project context:
   ```
   /ry-init
   ```

## Active Catalog

| Component | Description |
|---|---|
| **rldyour-mcps** (in opencode.json) | MCP transport: Serena, Sequential Thinking, Playwright, Context7, DeepWiki, Grep, GitHub, Figma |
| **rldyour-agents** (9 subagents) | Reviewer tracks (architecture, quality, consistency, integration, verification, security), memory sync, deep research |
| **rldyour-skills** (32 skills) | SDLC flow, Serena workflow, rules, research, browser, design, security, LSP |
| **rldyour-commands** (6 commands) | `/ry-init`, `/ry-start`, `/ry-review`, `/ry-newp`, `/ry-deploy`, `/ry-sync` |

## Commands

| Command | Description |
|---|---|
| `/ry-init` | Initialize scoped read-only project context with Serena-first discovery |
| `/ry-start` | Full task lifecycle: init → research → plan → implement → verify → review → sync |
| `/ry-review` | Deep review with research and reviewer subagents |
| `/ry-newp` | Plan a new project with skeptical questions and research |
| `/ry-deploy` | Deploy with sync, checks, and finalization |
| `/ry-sync` | Synchronize memories, docs, git, and fullrepo |

## Reviewer Subagents

Invoke via `@agent_name` in messages:

| Agent | Color | Focus |
|---|---|---|
| `@flow-architecture-review` | blue | Boundaries, dependencies, public API, data flow |
| `@flow-quality-review` | green | Correctness, edge cases, error handling |
| `@flow-consistency-review` | purple | Naming, style, project conventions |
| `@flow-integration-review` | orange | Cross-module contracts, schemas, configs |
| `@flow-verification-review` | pink | Tests, quality gates, browser/server evidence |
| `@flow-security-review` | red | OWASP, auth/authz, injection, secrets |
| `@flow-memory-sync` | yellow | Fact-only Serena memory synchronization |
| `@ry-explore` | cyan | Deep multi-source research (Opus, 1M context) |

## License

MIT