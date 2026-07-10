# Migration Mapping: Codex/Claude Code → OpenCode

> **Note (2026-05-14, supersession banner).** Example model IDs in code blocks
> below (`claude-sonnet-4-20250514`, `claude-haiku-4-20250514`,
> `claude-opus-4-20250514`) are historical and produce `ConfigInvalidError`
> against OpenCode v1.14.30+. As of 0.10.1, no model IDs are hardcoded in
> agent configs - all agents inherit from top-level `model` (currently `opencode-go/glm-5.1`).
> The ADR text itself is preserved unchanged. See `.serena/memories/CORE-02-PROJECT-SHAPE.md`
> for current config facts.
>
> **Browser-provider supersession (2026-06-08).** The MCP mapping table below
> is historical migration evidence. Current active browser automation uses
> Webwright, Playwright CLI, and Chrome DevTools MCP; Playwright MCP is not an
> active OpenCode MCP server.

## Commit History Analysis

### Codex (rldyour-codex) - 108 commits
Chronological evolution:
1. `aa53e1e` - Bootstrap marketplace (initial structure)
2. `7950e5f` - Stabilize MCP startup configuration
3. `18e5f63` - Refine plugin metadata
4. `c24fd12` - Add Serena MCP workflow plugin
5. `07db814` - Add OWASP security skills plugin
6. `9b93b2f` - Add Playwright/DevTools browser plugin
7. `11eab45` - Add Figma design plugin
8. `29b3027` - Improve automatic skill routing
9. `543630b` - Record design plugin routing facts
10. `5006272` - Add LSP and flow workflow plugins
11. `55229cd` - Add quality-first engineering rules plugin
12. `8c13e13` - Enforce Russian automatic routing
13. `03a05d1` - Add system install workflow
14. ... → Many iterations on hooks, validation, fullrepo, system install
15. Latest: `7825a59` - Reproduce managed system defaults

### Claude Code (rldyour-claudecode) - 87 commits
Chronological evolution:
1. `f43b3db` - Bootstrap rldyour-claude marketplace
2. `e3f6a02` - Add MCPs plugin with pinned servers
3. `4db3ec1` - Add Serena MCP plugin with lifecycle hooks
4. `4b31968` - Add explore plugin with deep-research subagent
5. `8caca31` - Add security plugin
6. `c5463ad` - Add browser plugin
7. `ce73b2d` - Design plugin
8. `9d3d24c` - Add LSPs plugin
9. `1c65b04` - Add rules plugin
10. `3943075` - Flow plugin base
11. ... → Hook lifecycle, worktree workflow, reviewer agents, bilingual descriptions
12. Latest: `ef18bd9` - v0.1.1 release refresh

**Pattern**: Both repos started with infrastructure (MCP), then added domain plugins one by one, then iterated heavily on lifecycle (hooks, validation, fullrepo, worktree).

## Migration Strategy

Since OpenCode has NO hooks system, the lifecycle automation pattern must change fundamentally:

### What maps directly
| Source Concept | OpenCode Target | Notes |
|---|---|---|
| SKILL.md | `.opencode/skills/*/SKILL.md` | Simplify frontmatter (remove `allowed-tools`, `model`, `effort`, `maxTurns`, `paths`, `context`, `agent`) |
| Agent .md | `.opencode/agents/*.md` | Change `maxTurns` → `steps`, `disallowedTools` → `permission` dict, add `mode: subagent` |
| Slash commands | `.opencode/commands/*.md` | New concept in OpenCode - `description` + `template` |
| MCP servers | `opencode.json` → `mcp` section | Convert from `.mcp.json` array to OpenCode's `mcp` object |
| LSP config | `opencode.json` → `lsp` section | Use OpenCode's 30+ built-in servers |
| References | `references/*.md` | Direct copy - Markdown reference docs are tool-agnostic |
| Serana memories | `.serena/memories/` | Direct copy - Serena is MCP-agnostic |
| AGENTS.md | `AGENTS.md` | Major rewrite - remove Codex/Claude specifics, add OpenCode instructions |

### What needs fundamental rethinking
| Source Concept | Problem | OpenCode Solution |
|---|---|---|
| Hook lifecycle (8 hooks) | OpenCode has NO hooks | AGENTS.md instructions + `/ry-init`, `/ry-sync` commands. Advisory, not enforcement. |
| `alwaysLoad: true` on Serena | MCP concept | OpenCode MCP servers start on-demand; configure in `opencode.json` `mcp` section with `enabled: true` |
| `allowed-tools` in skills | Not in OpenCode SKILL.md | Tool restrictions via agent `permission` config |
| `skillListingBudgetFraction` | CC-specific settings | Not needed - OpenCode has its own skill discovery system |
| `mcp__plugin_rldyour-mcps_<server>__*` tool names | CC naming convention | OpenCode uses `mcp__<servername>__<toolname>` pattern. Update in agent prompts and skill bodies. |
| `CLAUDE_PROJECT_DIR` env var | CC-specific | Not available in OpenCode - use `context.directory` / `context.worktree` in custom tools if needed |
| `${CLAUDE_PLUGIN_ROOT}` in hooks | CC-specific | Not available - references in skill bodies should use relative paths or skill references |
| `claude plugin validate/tag/prune` | CC CLI commands | Not available - use `scripts/validate_config.sh` or OpenCode's `/init` command |
| Reviewer agents `disallowedTools: [Edit, Write, NotebookEdit]` | CC-specific tool names | Map to OpenCode: `permission: { edit: "deny" }` which covers `write`, `edit`, `apply_patch` |
| `context: fork` in skills | CC concept | Not in OpenCode - remove from skill descriptions |
| `effort: high/max` in agents | CC concept | Map to OpenCode `temperature` (0.1 for focused, 0.3 for balanced) or omit for model default |
| `model: opus[1m]` bracketed syntax | CC-specific | Use OpenCode model IDs: `anthropic/claude-opus-4-20250514` or similar |
| `model: sonnet` short form | CC-specific | Use `anthropic/claude-sonnet-4-20250514` |
| System install scripts | Codex-specific | Adapt for OpenCode config directory structure (`~/.config/opencode/`) |

### MCP Server Mapping
| Server | Codex CC `.mcp.json` format | OpenCode `opencode.json` format |
|---|---|---|
| serena-agent | stdio with `--context=agent` | `{ "type": "local", "command": ["npx", "-y", "@anthropic/serena-mcp@1.3.0", "--context", "agent"] }` |
| sequential-thinking | stdio npm package | `{ "type": "local", "command": ["bunx", "@modelcontextprotocol/server-sequential-thinking@2026.7.4"] }` |
| playwright | stdio npm package | Historical only: retired Playwright MCP mapping; current provider is Playwright CLI, not an MCP server. |
| context7 | remote HTTP | `{ "type": "remote", "url": "https://mcp.context7.com/mcp" }` |
| deepwiki | remote HTTP | `{ "type": "remote", "url": "https://mcp.deepwiki.com/mcp" }` |
| grep | remote HTTP | `{ "type": "remote", "url": "https://mcp.grep.app" }` |
| github | remote HTTP with auth/toolsets | `{ "type": "remote", "url": "https://api.githubcopilot.com/mcp/", "headers": { "Authorization": "Bearer {env:GITHUB_PERSONAL_ACCESS_TOKEN}", "X-MCP-Toolsets": "context,repos,issues,pull_requests,users" } }` |
| figma | remote HTTP | `{ "type": "remote", "url": "https://mcp.figma.com/" }` |
| openai-docs | remote HTTP | `{ "type": "remote", "url": "https://openai-mcp-serverless.vercel.app/mcp" } or remove` |
| shadcn | stdio | `{ "type": "local", "command": ["bunx", "shadcn@4.13.0", "mcp"] }` |
| chrome-devtools | stdio | Remove - not available as npm package |
| dart | stdio | `{ "type": "local", "command": ["dart", "mcp-server"] } or use OpenCode built-in LSP` |

### OpenCode Built-in Replacements
| Feature | Codex/Claude Plugin | OpenCode Built-in |
|---|---|---|
| LSP (30+ languages) | `.lsp.json` per plugin | `opencode.json` → `lsp: true` or custom config |
| Web search | DeepWiki/Grep MCP | Built-in `websearch` tool (with `OPENCODE_ENABLE_EXA=1` or Zen) |
| File search | Custom skills | Built-in `grep`, `glob` tools |
| Web fetch | Custom skill | Built-in `webfetch` tool |
| Read/edit/write | Custom skill | Built-in `read`, `edit`, `write` tools |
| Bash execution | Custom hook scripts | Built-in `bash` tool |
| Question to user | N/A | Built-in `question` tool |
| Todo tracking | N/A | Built-in `todowrite` tool |
| Skill loading | Custom skill system | Built-in `skill` tool + `.opencode/skills/*/SKILL.md` |
