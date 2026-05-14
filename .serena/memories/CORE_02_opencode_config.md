# CORE_02 OpenCode Configuration

Verified facts about `opencode.json` at HEAD 1f1510b.
Source: `opencode.json` (208 lines), parsed via direct read.

Last commit: 1f1510b

## Top-Level Keys

`$schema`, `model`, `small_model`, `autoupdate`, `share`, `snapshot`, `shell`, `lsp`, `permission`, `agent`, `mcp`, `instructions`, `compaction`, `plugin`, `watcher`

## Models

- `model`: `opencode-go/glm-5.1` (primary, user-selected — all agents inherit this)
- `small_model`: `opencode-go/glm-5.1` (fallback — same as primary, no separate lightweight model)
- `default_agent`: `"build"` (explicit primary selection)
- No per-agent model overrides — all agents inherit from top-level `model`. Agent blocks only set `mode`, `permission`, `temperature`, `steps`, `hidden`, `color`.
- `ry-explore` subagent has no model override — inherits top-level `model`.

## Global Settings

- `autoupdate`: true
- `share`: "manual"
- `snapshot`: true
- `shell`: "/bin/zsh"
- `instructions`: ["AGENTS.md"]
- `compaction`: { auto: true, prune: true, tail_turns: 12, preserve_recent_tokens: 8000, reserved: 4000 }
- `plugin`: [] (empty — plugins are auto-discovered from `.opencode/plugins/`, not listed here)

## Global Permission Block

Source: `opencode.json` → `permission` key

```json
{
  "edit": "allow",
  "bash": "allow",
  "webfetch": "allow",
  "websearch": "allow",
  "lsp": "allow",
  "skill": "allow",
  "glob": "allow",
  "grep": "allow",
  "read": "allow"
}
```

## Primary Agent Overrides

Source: `opencode.json` → `agent` key

**build** (mode: primary):
- No model override — inherits top-level `model` (opencode-go/glm-5.1)
- permissions: edit/bash/webfetch/websearch/lsp/skill/task/todowrite/question — all allow

**plan** (mode: primary):
- No model override — inherits top-level `model`
- permissions: edit=ask, bash=ask; webfetch/websearch/lsp/skill — allow

**title** (built-in hidden agent):
- No model override — inherits top-level `model`
- temperature: 0.2

**summary** (built-in hidden agent):
- No model override — inherits top-level `model`
- temperature: 0.2

**compaction** (built-in hidden agent):
- No model override — inherits top-level `model`
- temperature: 0.2

Note: subagent definitions (flow-*, ry-explore, customize-opencode) live ONLY in `.opencode/agents/*.md`, not in opencode.json.

## Compaction Block

Source: `opencode.json` lines 186-192

```json
{
  "auto": true,
  "prune": true,
  "tail_turns": 12,
  "preserve_recent_tokens": 8000,
  "reserved": 4000
}
```

Source for `tail_turns`, `preserve_recent_tokens`, `reserved`: OpenCode v2 SDK types (`dist/gen/types.gen.d.ts`).

## MCP Servers (13)

Source: `opencode.json` → `mcp` key (13 entries). Timeouts in milliseconds.

| Server | Type | Launcher / URL | Version | Timeout |
|---|---|---|---|---|
| serena | local | `uvx serena-agent==1.3.0` | 1.3.0 | 30000 |
| sequential-thinking | local | `bunx @modelcontextprotocol/server-sequential-thinking@2025.12.18` | 2025.12.18 | 30000 |
| playwright | local | `bunx @playwright/mcp@0.0.75 --headless` | 0.0.75 | 30000 |
| chrome-devtools | local | `bunx chrome-devtools-mcp@0.25.0 --headless --isolated` | 0.25.0 | 30000 |
| context7 | remote | https://mcp.context7.com/mcp | — | 15000 |
| deepwiki | remote | https://mcp.deepwiki.com/mcp | — | 15000 |
| grep | remote | https://mcp.grep.app | — | 15000 |
| semgrep | local | `uvx semgrep==1.162.0` | 1.162.0 | 30000 |
| shadcn | local | `bunx shadcn@4.7.0 mcp` | 4.7.0 | 30000 |
| dart-flutter | local | `dart mcp-server --force-roots-fallback` | — | 30000 |
| figma | remote | https://mcp.figma.com/mcp | — | 15000 |
| github | remote | https://api.githubcopilot.com/mcp/ (Bearer {env:GITHUB_PERSONAL_ACCESS_TOKEN}) | — | 15000 |
| openai-docs | remote | https://developers.openai.com/mcp | — | 15000 |

Pattern: local servers 30s timeout; remote servers 15s timeout. Launcher rule: `bunx` for npm, `uvx` for Python, `dart` for Dart SDK. Never `npx`.

Required env vars (source: `.env.example`): `CONTEXT7_API_KEY` (optional, higher rate limits), `GITHUB_PERSONAL_ACCESS_TOKEN` (required for github MCP).

## Custom LSP Servers (8)

Source: `opencode.json` → `lsp` key. These are additions atop OpenCode's 35+ built-in LSP servers.

| Key | Command | File Extensions |
|---|---|---|
| ruff | `ruff server` | `.py`, `.pyi` |
| vscode-html | `vscode-html-language-server --stdio` | `.html`, `.htm` |
| vscode-css | `vscode-css-language-server --stdio` | `.css`, `.scss`, `.sass`, `.less` |
| vscode-json | `vscode-json-language-server --stdio` | `.json`, `.jsonc` |
| docker | `docker-language-server start --stdio` | `.dockerfile` |
| taplo | `taplo lsp stdio` | `.toml` |
| marksman | `marksman server` | `.md`, `.mdx`, `.markdown` |
| qmlls | `qmlls` | `.qml` |

Source of `vscode-*` servers: `vscode-langservers-extracted` package.

## Watcher

Source: `opencode.json` → `watcher.ignore` (11 paths, expanded in commit `cbe9547`)

```json
{
  "ignore": [
    "node_modules/**",
    "dist/**",
    ".git/**",
    "browser/**",
    ".serena/cache/**",
    ".opencode/node_modules/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    ".cache/**",
    ".venv/**",
    "**/*.log"
  ]
}
```
