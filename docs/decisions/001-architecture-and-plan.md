# rldyour-opencode Architecture and Implementation Plan

> **Note (2026-05-13, supersession banner).** Example model IDs in code blocks
> below (`claude-sonnet-4-20250514`, `claude-haiku-4-20250514`,
> `claude-opus-4-20250514`) are historical and produce `ConfigInvalidError`
> against OpenCode v1.14.30+. Use the current registry IDs:
> `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-opus-4-7`.
> The ADR text itself is preserved unchanged — only the example IDs are
> obsolete. See `CHANGELOG.md` 0.5.0 and `.serena/memories/CORE_02_opencode_config.md`
> for migration context.

## Marketplace Question

OpenCode does **NOT** have a plugin marketplace like Claude Code (`claude plugin validate/install/tag`) or Codex (`.codex-plugin/plugin.json`). OpenCode's extension system is:

- **`opencode.json`** — single config file for everything (providers, models, agents, tools, permissions, commands, themes, keybinds, formatters, LSP, MCP, skills)
- **`.opencode/`** directory — agents, skills, commands, themes, plugins (npm)
- **NPM plugins** — can be loaded via `plugin` key in opencode.json (e.g. `"plugin": ["opencode-helicone-session"]`)
- **No `marketplace.json`** — no manifest catalog, no `$schema` for plugin manifests, no `plugin validate/tag` CLI commands

**Decision**: Instead of a marketplace, rldyour-opencode distributes as a **git repository with complete `opencode.json` config + `.opencode/` skill/agent/command definitions**. Users clone or copy into their project. This mirrors how OpenCode's own `.opencode/` convention works — skills, agents, and commands are project-local.

A future npm package (`opencode-ai/rldyour-opencode` or similar) could wrap the `.opencode/` directory and `opencode.json` partial as an installable plugin, but that depends on OpenCode's plugin SDK maturity and is **Phase 4**.

---

## Architecture Overview

```
rldyour-opencode/
├── AGENTS.md                           # Cross-tool root instructions
├── opencode.json                       # Master config: model, providers, agents, 
│                                       #   permissions, MCP, LSP, commands, tools
├── .opencode/
│   ├── agents/                         # Subagent definitions (YAML frontmatter + prompt)
│   │   ├── flow-architecture-review.md
│   │   ├── flow-quality-review.md
│   │   ├── flow-consistency-review.md
│   │   ├── flow-integration-review.md
│   │   ├── flow-verification-review.md
│   │   ├── flow-security-review.md
│   │   ├── flow-memory-sync.md
│   │   └── ry-explore.md
│   ├── skills/                         # On-demand skill definitions
│   │   ├── ry-init/SKILL.md
│   │   ├── ry-start/SKILL.md
│   │   ├── ry-review/SKILL.md
│   │   ├── ry-newp/SKILL.md
│   │   ├── ry-deploy/SKILL.md
│   │   ├── flow-post-task-sync/SKILL.md
│   │   ├── instruction-docs-sync/SKILL.md
│   │   ├── serena-code-workflow/SKILL.md
│   │   ├── serena-memory-sync/SKILL.md
│   │   ├── quality-first-engineering/SKILL.md
│   │   ├── architecture-boundaries/SKILL.md
│   │   ├── implementation-discipline/SKILL.md
│   │   ├── dependency-compatibility-policy/SKILL.md
│   │   ├── verification-quality-gates/SKILL.md
│   │   ├── project-instructions-policy/SKILL.md
│   │   ├── ry-rules-review/SKILL.md
│   │   ├── lsp-routing/SKILL.md
│   │   ├── lsp-health-check/SKILL.md
│   │   ├── lsp-setup/SKILL.md
│   │   ├── serena-lsp-integration/SKILL.md
│   │   ├── browser-tool-routing/SKILL.md
│   │   ├── browser-validation/SKILL.md
│   │   ├── browser-debug/SKILL.md
│   │   ├── design-validation/SKILL.md
│   │   ├── figma-to-code/SKILL.md
│   │   ├── design-system-implementation/SKILL.md
│   │   ├── fsd-frontend-architecture/SKILL.md
│   │   ├── ry-design/SKILL.md
│   │   ├── owasp-top-10-implementation/SKILL.md
│   │   ├── ry-sec-review/SKILL.md
│   │   ├── tech-research/SKILL.md
│   │   └── web-research/SKILL.md
│   └── commands/                        # Slash commands (OpenCode custom commands)
│       ├── ry-init.md
│       ├── ry-start.md
│       ├── ry-review.md
│       ├── ry-newp.md
│       ├── ry-deploy.md
│       └── ry-sync.md
├── scripts/                            # Validation, bootstrap, diagnostics
│   ├── validate_config.sh
│   ├── bootstrap_opencode.sh
│   └── doctor_opencode.sh
├── references/                         # Reference docs for skills/agents
│   ├── init-context-pack.md
│   ├── post-task-sync.md
│   ├── flow-lifecycle.md
│   ├── deploy-contract.md
│   ├── reviewer-protocol.md
│   ├── sources.md
│   ├── context-sufficiency-gate.md
│   ├── rules-policy.md
│   ├── architecture-policy.md
│   ├── dependency-policy.md
│   ├── quality-gates.md
│   ├── project-instructions-and-adrs.md
│   ├── lsp-server-matrix.md
│   ├── serena-lsp-integration.md
│   └── install-profiles.md
├── .serena/                            # Serena project state (if used)
│   ├── project.yml
│   └── memories/
├── .gitignore
├── README.md
├── VERSION
├── CHANGELOG.md
└── LICENSE
```

---

## OpenCode Format Rules (from docs)

### SKILL.md format
```markdown
---
name: skill-name
description: 1-1024 char description
license: MIT (optional)
compatibility: opencode (optional)
metadata: (optional string-to-string map)
---

# Skill Title

Skill body content...
```

**Critical**: OpenCode does NOT support `allowed-tools`, `disable-model-invocation`, `model`, `effort`, `maxTurns`, `paths`, `context`, or `agent` keys in SKILL.md frontmatter. These are Claude Code-specific. In OpenCode, tool access is controlled via agent `permission` config, and model/effort is set per-agent in `opencode.json`.

### Agent markdown format (.opencode/agents/*.md)
```markdown
---
description: Agent description
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
permission:
  edit: deny
  bash:
    "*": ask
    "git diff": allow
    "git log*": allow
  webfetch: deny
prompt: |
  You are a code reviewer...
---

Additional prompt content (optional)
```

**Key fields**: `description` (required), `mode` (primary/subagent), `model`, `temperature`, `top_p`, `steps` (max agentic iterations), `permission`, `hidden`, `color`, `prompt`.

### opencode.json config
Full schema at https://opencode.ai/config.json. Key sections:
- `model` / `small_model` — default models
- `provider` — API key config per provider
- `agent` — override built-in agents or define custom ones
- `permission` — tool access control (allow/ask/deny with glob patterns)
- `command` — custom slash commands with template, description, agent, model
- `mcp` — MCP server config (local command-based or remote URL-based with OAuth)
- `lsp` — LSP server config (true for all built-in, or object for custom)
- `formatter` — code formatter config
- `instructions` — paths/globs to instruction files
- `theme` / `keybinds` — TUI customization
- `share` — sharing mode (manual/auto/disabled)
- `snapshot` — snapshot tracking (true/false)
- `autoupdate` — auto-update behavior
- `shell` — shell config
- `server` — server config for `opencode serve`
- `plugin` — npm plugins to load
- `experimental` — experimental features

### Custom commands (.opencode/commands/*.md)
```markdown
---
description: Run tests with coverage
agent: build
model: anthropic/claude-haiku-4-20250514
---

Run the full test suite with coverage report and show any failures.
Focus on the failing tests and suggest fixes.
```

---

## Phased Implementation Plan

### Phase 1: Foundation (Core Config + AGENTS.md)
Based on Codex commit `aa53e1e bootstrap rldyour codex marketplace` and Claude commit `f43b3db init: bootstrap rldyour-claude marketplace`.

Files:
- `AGENTS.md` — OpenCode-specific root instructions
- `opencode.json` — Master config with model, provider, MCP servers, LSP, agents, permissions, commands
- `.opencode/agents/` — Subagent definitions (7 reviewers + memory-sync + explore)
- `.gitignore`
- `README.md`, `VERSION`, `CHANGELOG.md`, `LICENSE`

### Phase 2: Skills (32 skills)
Based on Codex commits adding skills plugin-by-plugin and Claude commit `ef1b819 feat(skills): bilingual trigger surface across all 32 skills`.

All 32 SKILL.md files adapted to OpenCode format (simpler frontmatter, tool routing via content not frontmatter).

### Phase 3: Commands, References, Scripts
Based on Codex commits for flow commands, validation scripts, bootstrap.

- `.opencode/commands/` — 6 slash commands
- `references/` — Reference docs
- `scripts/` — Validation and bootstrap scripts adapted for OpenCode CLI

### Phase 4: Git, Serena, CI/CD
Based on both repos' fullrepo workflow, git hooks, and CI.

- `.serena/` — Project state
- `.github/workflows/` — CI validation
- Fullrepo sync adapted for OpenCode (no hooks — instead, `/ry-sync` command)

---

## Critical Adaptations from Codex/Claude → OpenCode

| Feature | Codex | Claude Code | OpenCode |
|---|---|---|---|
| Hook lifecycle | Codex hooks (4 events) | CC hooks (30 events) | **NO hooks** — use AGENTS.md instructions + commands |
| SERENA sync enforcement | Stop hook blocks exit | Stop hook blocks exit | **Manual** — `/ry-sync` command + AGENTS.md instruction |
| Marketplace | `.agents/plugins/marketplace.json` | `.claude-plugin/marketplace.json` | **None** — `opencode.json` + `.opencode/` |
| Plugin manifest | `.codex-plugin/plugin.json` | `.claude-plugin/plugin.json` | **None** — config in `opencode.json` |
| Skills routing | OpenAI YAML + SKILL.md | CC SKILL.md with `allowed-tools` | OpenCode SKILL.md (name + description only) |
| Agent spec | OpenAI YAML | CC agent .md with frontmatter | OpenCode agent .md with frontmatter |
| MCP config | `.mcp.json` per plugin | `.mcp.json` per plugin | `opencode.json` → `mcp` section |
| LSP config | N/A | `.lsp.json` per plugin | `opencode.json` → `lsp` section |
| Reviewer subagents | OpenAI YAML | CC agent .md | OpenCode agent .md with `mode: subagent` |
| Model syntax | GPT model names | `sonnet`, `opus[1m]` | `provider/model-id` format |
| Permission system | N/A | `disallowedTools` | `permission` with `allow/ask/deny` + glob patterns |
| Slash commands | N/A | CC skill frontmatter | `.opencode/commands/*.md` |
| Serena memory sync | Subagent invoked by Stop hook | Subagent invoked by Stop hook | `/ry-sync` command invokes `serena-memory-sync` skill |