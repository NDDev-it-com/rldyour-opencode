# OpenCode Format Reference

> **Note (2026-05-13, supersession banner).** Example model IDs in code blocks
> below (`claude-sonnet-4-20250514`, `claude-haiku-4-20250514`,
> `claude-opus-4-20250514`) are historical and produce `ConfigInvalidError`
> against OpenCode v1.14.30+. Use the current registry IDs:
> `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-opus-4-7`.
> The ADR text itself is preserved unchanged — only the example IDs are
> obsolete. See `CHANGELOG.md` 0.5.0 and `.serena/memories/CORE_02_opencode_config.md`
> for migration context.

## Skill Format (.opencode/skills/*/SKILL.md)

```markdown
---
name: skill-name
description: Russian-leading description for auto-routing. EN triggers: english keywords.
---

# Skill Title

Body content in Markdown...
```

### Rules (from OpenCode docs):
- `name` — required, 1-64 chars, lowercase alphanumeric + single hyphens, must match directory name
- `description` — required, 1-1024 chars, specific enough for agent to choose correctly
- `license` — optional
- `compatibility` — optional
- `metadata` — optional string-to-string map
- NO `allowed-tools`, NO `disable-model-invocation`, NO `model`, NO `effort`, NO `maxTurns`, NO `paths`, NO `context`, NO `agent`
- Tool routing is done through AGENTS.md instructions and agent `permission` config

### Discovery:
OpenCode searches these locations:
1. Project: `.opencode/skills/*/SKILL.md`
2. Global: `~/.config/opencode/skills/*/SKILL.md`
3. Claude-compatible: `.claude/skills/*/SKILL.md` and `~/.claude/skills/*/SKILL.md`
4. Agent-compatible: `.agents/skills/*/SKILL.md` and `~/.agents/skills/*/SKILL.md`

---

## Agent Format (.opencode/agents/*.md)

```markdown
---
description: Agent description (required)
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
steps: 36
permission:
  edit: deny
  bash:
    "*": ask
    "git diff": allow
    "git log*": allow
  webfetch: deny
  read: allow
  glob: allow
  grep: allow
  lsp: allow
color: blue
prompt: |
  You are a code reviewer. Focus on security, performance, and maintainability.
---

Additional prompt content...
```

### Rules (from OpenCode docs):
- `description` — required
- `mode` — `primary` or `subagent`
- `model` — provider/model-id format (e.g., `anthropic/claude-sonnet-4-20250514`)
- `temperature` — 0.0-1.0
- `top_p` — 0.0-1.0
- `steps` — max agentic iterations (replaces deprecated `maxSteps`)
- `permission` — granular allow/ask/deny with glob patterns
- `hidden` — boolean, hides from @ autocomplete for subagents
- `color` — hex color or theme color name
- `prompt` — custom system prompt (can use `{file:./prompts/build.txt}` reference)
- Additional keys are passed through to the provider as model options

### Permission keys:
| Key | Tools it gates |
|---|---|
| `read` | `read` |
| `edit` | `write`, `edit`, `apply_patch` |
| `glob` | `glob` |
| `grep` | `grep` |
| `list` | `list` |
| `bash` | `bash` |
| `task` | `task` |
| `external_directory` | Any tool that reads/writes outside project worktree |
| `todowrite` | `todowrite`, `todoread` |
| `webfetch` | `webfetch` |
| `websearch` | `websearch` |
| `lsp` | `lsp` |
| `skill` | `skill` |
| `question` | `question` |

### Built-in agents (can override):
- `build` — default primary, all tools enabled
- `plan` — restricted primary, edit/bash ask by default

### Subagent invocation:
- Primary agents switch via Tab key
- Subagents invoked via `@agent_name` in messages
- Task tool: agents can invoke subagents via the Task tool

---

## Command Format (.opencode/commands/*.md)

```markdown
---
description: Run tests with coverage
agent: build
model: anthropic/claude-haiku-4-20250514
---

Run the full test suite with coverage report and show any failures.
Focus on the failing tests and suggest fixes.
```

### Also in opencode.json:
```json
{
  "command": {
    "test": {
      "template": "Run the full test suite with coverage report and show any failures.",
      "description": "Run tests with coverage",
      "agent": "build",
      "model": "anthropic/claude-haiku-4-20250514"
    }
  }
}
```

---

## MCP Config (in opencode.json)

### Local MCP server:
```json
{
  "mcp": {
    "serena": {
      "type": "local",
      "command": ["npx", "-y", "@anthropic/serena-mcp@1.3.0", "--context", "agent"],
      "enabled": true,
      "environment": {
        "SERENA_AGENT_VERSION": "1.3.0"
      }
    }
  }
}
```

### Remote MCP server:
```json
{
  "mcp": {
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp",
      "enabled": true
    }
  }
}
```

### Remote with auth:
```json
{
  "mcp": {
    "github": {
      "type": "remote",
      "url": "https://api.githubcopilot.com/mcp/",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer {env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

---

## LSP Config (in opencode.json)

```json
{
  "lsp": true
}
```

Or with overrides:
```json
{
  "lsp": {
    "typescript": { "disabled": true },
    "custom-lsp": {
      "command": ["custom-lsp-server", "--stdio"],
      "extensions": [".custom"]
    }
  }
}
```

OpenCode has 30+ built-in LSP servers that auto-start when file extensions are detected.

---

## Permissions (in opencode.json)

Global:
```json
{
  "permission": {
    "edit": "allow",
    "bash": "allow",
    "webfetch": "allow",
    "websearch": "allow",
    "lsp": "allow"
  }
}
```

Per-agent override:
```json
{
  "agent": {
    "flow-architecture-review": {
      "permission": {
        "edit": "deny",
        "bash": { "*": "ask", "git diff": "allow", "git log*": "allow" },
        "webfetch": "deny"
      }
    }
  }
}
```

---

## Model ID Format

OpenCode uses `provider/model-id` format:
- `anthropic/claude-sonnet-4-20250514`
- `anthropic/claude-haiku-4-20250514`
- `openai/gpt-5`
- `opencode/gpt-5.1-codex` (Zen)
- `google/gemini-2.5-pro`
- `deepseek/deepseek-v4`

---

## OpenCode Built-in Tools

`bash`, `edit`, `write`, `read`, `grep`, `glob`, `apply_patch`, `lsp` (experimental), `skill`, `todowrite`, `webfetch`, `websearch`, `question`

MCP tool names follow pattern: `mcp__<servername>__<toolname>` (shown in permission config as `mymcp_*` glob)

---

## Key Differences from Codex/Claude Code Implementation

1. **No hooks lifecycle** — All lifecycle automation (Serena sync, commit advice, context bootstrap) moves to:
   - AGENTS.md instructions (advisory)
   - `/ry-init` and `/ry-sync` commands (user-invoked)
   - Agent system prompts (enforcement through agent permission config)

2. **No marketplace.json** — All config in `opencode.json` and `.opencode/` directory

3. **Skill frontmatter is minimal** — Only `name` and `description`. No `allowed-tools`, `model`, `effort`, `maxTurns`. Tool access is per-agent, model selection is per-agent or per-command.

4. **Agent format uses YAML frontmatter in .md** — Similar to Claude Code but with different keys (`mode`, `steps`, `permission` dict instead of `maxTurns`, `disallowedTools`)

5. **Permission system is powerful** — Glob patterns on bash commands, per-tool allow/ask/deny, per-agent overrides

6. **Built-in websearch** — Available with `OPENCODE_ENABLE_EXA=1` env var or via Zen provider

7. **Built-in LSP** — 30+ servers, much more than Codex (none) or Claude Code (manual `.lsp.json`)