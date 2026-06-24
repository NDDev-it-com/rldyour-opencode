# OpenCode Plugin Patterns

Reference for the advanced `@opencode-ai/plugin` hook surface used by this marketplace. Sourced from `.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts` v1.17.7 (pin bumped from v1.15.3, originally introduced from v1.14.48 - the runtime hook surface and tool-ID format are unchanged across these versions); cross-checked against https://opencode.ai/docs/plugins/.

## Plugin context

Every plugin factory receives:

```ts
PluginInput = {
  client: ReturnType<typeof createOpencodeClient>  // SDK client for server API
  project: Project                                 // { id, worktree, vcsDir?, vcs?, time }
  directory: string                                // process working directory
  worktree: string                                 // git worktree root
  experimental_workspace: { register: (type, adapter) => void }
  serverUrl: URL
  $: BunShell                                      // Bun shell helper
}
```

`Project` shape per `@opencode-ai/sdk` `gen/types.gen.d.ts:607` exposes `id`, `worktree`, `vcsDir?`, `vcs?`, and a `time` object. The `name` and `path` fields used to exist only as informal runtime extensions; they are NOT typed by the SDK and casting `project as { name?: string; path?: string }` is dead surface. Use `project.worktree` for the project directory and `directory` for the process working directory (always defined per `PluginInput` contract). Project name can be derived from the basename of `worktree`. The cast guard is enforced by `scripts/tests/test_plugin_surface.py::test_no_dead_project_path_cast_in_plugins`.

## Hook surface (server-side)

All hooks live under the returned `Hooks` object. Each is optional.

### Observation / lifecycle

| Hook | When | Use case |
|---|---|---|
| `event` | Many events under `event.type` discriminator (session.*, file.*, message.*, todo.*, lsp.*, command.*, installation.*, server.connected) | Logging, banners, idle reminders |
| `config` | Config resolved | Inspect or augment runtime config |

### Tool registration (custom tools)

Register tools the LLM can call:

```ts
import { tool } from "@opencode-ai/plugin"

return {
  tool: {
    rldyour_my_tool: tool({
      description: "What this tool does. Visible to the LLM.",
      args: {                              // Zod shape
        path: tool.schema.string(),
        verbose: tool.schema.boolean().optional(),
      },
      async execute(args, ctx) {           // ctx: ToolContext
        // ctx.directory, ctx.worktree, ctx.sessionID, ctx.abort
        return "string result"
        // or: { output: "...", metadata: { ... } }
      },
    }),
  },
}
```

`ToolContext` exposes `metadata({ title, metadata })` so the tool can stamp the call with structured data shown in the TUI. Use `abort` (an `AbortSignal`) to cancel long-running work cooperatively.

### Pipeline modification

| Hook | When | What it can change |
|---|---|---|
| `chat.message` | New user message received | Read message + parts |
| `chat.params` | Before sending to LLM | `temperature`, `topP`, `topK`, `maxOutputTokens`, `options` |
| `chat.headers` | Before sending to LLM | HTTP headers (e.g., provider-specific auth) |
| `tool.execute.before` | Before tool runs | Throw to block, mutate `output.args` |
| `tool.execute.after` | After tool runs | Inspect `output` |
| `tool.definition` | Sent to LLM | Modify `description` / `parameters` |
| `shell.env` | Each shell spawn | Inject `env` vars |
| `command.execute.before` | Slash command starts | Read `command`, `arguments`, `sessionID`; emit `parts` |
| `permission.ask` | SDK type, source-inspected in v1.15.4 | **Forbidden for enforcement** in this repo; source/runtime inspection found no trigger path in OpenCode v1.15.4 and the current v1.17.9 baseline keeps this policy |

> **Security note on `permission.ask`.** OpenCode's plugin SDK exposes this hook type, but v1.15.4 source/runtime inspection showed that the permission service publishes `permission.asked` / `permission.replied` bus events and does not trigger plugin-level `permission.ask`. The current v1.17.9 baseline keeps this hook forbidden for enforcement. Static permission config is the primary policy; dynamic denial must use runtime-proven hooks such as `tool.execute.before`. `scripts/check_plugin_hooks.py` rejects `permission.ask` in plugin code.

### Auth / provider extension

| Hook | Purpose |
|---|---|
| `auth` | Define a custom auth method (OAuth / API key prompt flow) for a provider |
| `provider` | Register additional models for an existing provider via the SDK v2 `Provider` / `Model` types |

### Compaction

| Hook | Purpose |
|---|---|
| `experimental.session.compacting` | Append context strings or fully replace the compaction prompt |
| `experimental.compaction.autocontinue` | Toggle the synthetic "continue" turn that fires after compaction |

### System / text shaping

| Hook | Purpose |
|---|---|
| `experimental.chat.messages.transform` | Rewrite message history sent to the LLM |
| `experimental.chat.system.transform` | Append project-specific system prompt segments |
| `experimental.text.complete` | Modify completed text output |

### TUI hooks (separate module)

`@opencode-ai/plugin/tui.d.ts` exposes `tui.prompt.append`, `tui.command.execute`, `tui.toast.show`. These require `PluginModule.tui` (different from the server `Plugin` factory) and are not used by this repo.

## Patterns adopted in this marketplace

### Custom diagnostic tools (`.opencode/plugins/ry-tools.ts`)

Five tools registered, all wrapping existing diagnostic scripts so the LLM can drive them directly without a bash round-trip:

- `rldyour_validate_config` - runs `scripts/validate_config.sh`.
- `rldyour_check_deps` - runs `scripts/check_deps_freshness.sh --json`.
- `rldyour_lsp_health` - runs `scripts/check_lsps.sh`.
- `rldyour_git_audit` - runs `scripts/git_sync_audit.sh`.
- `rldyour_fullrepo_status` - runs `scripts/fullrepo_sync.sh status-json`.

Each tool returns the script's combined stdout/stderr and stamps `ctx.metadata({ title, metadata: { exitCode } })` so the TUI shows pass/fail at a glance.

### Slash-command audit (`.opencode/plugins/ry-command-audit.ts`)

`command.execute.before` appends one line per slash command invocation to `.serena/.command_audit.log` (runtime marker - never committed). Args are sanitized for credential-shaped patterns before logging. Log rotates with reset when it crosses 256 KiB.

### Tool routing nudges (`.opencode/plugins/ry-tool-hints.ts`)

`tool.definition` appends one short routing hint per known MCP tool ID. Hints encode the AGENTS.md tool-priority matrix (e.g., "Use Serena `find_symbol` before raw grep") so the LLM has the routing rule in the tool description itself, not just the high-level AGENTS.md instructions.

HINTS keys use the OpenCode `<server>_<tool>` tool-ID format (single underscore; dashes preserved; introduced in v1.14.48, unchanged through the current v1.17.9 baseline). Example: `serena_find_symbol`, `chrome-devtools_list_console_messages`, `context7_resolve-library-id`. The Claude-Code-style `mcp__server__tool` prefix silently disables every hint and is banned by `scripts/tests/test_plugin_surface.py::test_ry_tool_hints_no_legacy_aliases`.

### Permission event audit (`.opencode/plugins/ry-permission-events.ts`)

`event` observer for `permission.asked` and `permission.replied`. It writes short, non-secret audit lines to `client.app.log` with session/request IDs and the permission/reply value. It never sets policy, never auto-allows, and never blocks. This separation is intentional: permission enforcement is static config plus `ry-shell-strategy.ts`; permission events are observability only.

### Dynamic system prompt context (`.opencode/plugins/ry-system-context.ts`)

`experimental.chat.system.transform` injects a one-line runtime stamp into every system prompt: `[rldyour runtime] date=YYYY-MM-DD branch=... head=<short> worktree=clean|dirty(N files)`. Probes git via `Bun.spawn` with silent fallback ("unknown" when git unavailable). Branch and HEAD flow through a per-directory TTL cache (3 s; audit P1-6 + integration-review F-3 + reviewer wave closures) so an in-session `git checkout|switch|rebase` invalidates the stamp within one turn while still suppressing two of the three subprocess spawns per turn. `git status --porcelain` is the only turn-volatile probe and spawns every call. Both `branch` and `headShort` flow through a `sanitizeRuntimeStamp` allowlist `[A-Za-z0-9._/-]` with a `SAFE_STAMP_MAX_LEN` cap before reaching the system prompt - defeats indirect prompt injection through crafted branch names (reviewer wave 2026-05-18 security F-4 closure). Grounds the LLM in "now" facts that the static AGENTS.md cannot carry.

### Compaction autocontinue suppression (`.opencode/plugins/ry-bootstrap.ts`)

`experimental.compaction.autocontinue` sets `output.enabled = false` when `input.overflow` is true. The default synthetic "continue" turn after context-overflow compaction wastes tokens on reviewer / security / sync agents that already produced a final report. Letting the user (or orchestrating skill) choose the next prompt is cleaner than auto-generating filler.

### Observability: `client.app.log` + `client.tui.showToast`

All 10 plugins use the OpenCode v1.14.48+ client API for user-visible and structured logging instead of `console.log` (which lands only in the server log file `~/.local/share/opencode/log/*.log` and is invisible to the user). The current runtime/plugin/SDK baseline is v1.17.9; several historical implementation notes above were originally validated against v1.15.4 and remain historical evidence only:

```ts
async function log(level: "info" | "warn" | "error", message: string) {
  try {
    await client.app.log({ body: { service: "<plugin-name>", level, message } })
  } catch { /* server log unavailable; carry on */ }
}

async function toast(variant: "info" | "warning" | "error", message: string) {
  try {
    await client.tui.showToast({ body: { variant, message } })
  } catch { /* tui unavailable; carry on */ }
}
```

Both helpers are best-effort - a transient client error never blocks the underlying tool execution. The `service` field per `client.app.log` matches the plugin file stem (`ry-shell-strategy`, `ry-flow-hooks`, etc.) for grep-friendly filtering. Toast `variant` set as `"warning"` for advisory, `"error"` for blocks; `"info"` only for low-frequency banners (idle reminder, post-commit `/ry-sync` nudge). Console.log is reserved for unit-test fixtures or temporary debugging - production plugins must not use it.

### Session bootstrap context (`.opencode/plugins/ry-bootstrap.ts`)

`event` (`session.created`) surfaces a one-line bootstrap message via `client.app.log` (not `console.log`). `experimental.session.compacting` injects the active MCP server list (read live from `opencode.json` via `Bun.file()`), reviewer subagent list, workflow sequence, and quality rules. The reviewer list is hardcoded (it is stable); the MCP list is dynamic.

### Sensitive-path guard (`.opencode/plugins/ry-env-protection.ts`)

`tool.execute.before` throws on reads / bash commands that touch `.env*`, `.pem`, `.key`, `.p12`, `.pfx`, `.ssh`, `.gnupg`, `.aws`, `secret`, `private_key`, `service_account` paths. Whitelist: `.env.example`, `.env.template`, `.env.sample`.

### Shell hardening (`.opencode/plugins/ry-shell-strategy.ts`)

`shell.env` injects non-interactive git/CI env (`GIT_TERMINAL_PROMPT=0`, `CI=1`, `NODE_OPTIONS=--max-old-space-size=4096`). `tool.execute.before` is the unconditional dynamic enforcement layer for shell hardening: throws on `git push --force` / `-f` without `--force-with-lease`, catastrophic `rm -rf` targets (`/`, `$HOME`, `~`, cwd, parent dir; `node_modules` allowlist), and `git push --no-verify` unless `RY_ALLOW_NO_VERIFY=1` is set in the shell environment. It also warns on non-catastrophic recursive `rm` and surfaces a quality checklist on ordinary `git push`. The hook fires regardless of static permission config.

### Session-idle reminder (`.opencode/plugins/ry-sync-reminder.ts`)

`event` filter on `session.idle` surfaces an end-of-session reminder via `client.tui.showToast` (8 s duration) plus one `client.app.log` line for the audit trail.

### Post-commit Conventional Commits advice (`.opencode/plugins/ry-flow-hooks.ts`)

`tool.execute.after` parses `git commit` output, checks the subject against the Conventional Commits regex, and surfaces format advice as a `toast("warning", ...)` on miss. Also nudges `/ry-sync` as a `toast("info", ...)` after `git commit|merge|cherry-pick|rebase`. Sole owner of post-commit advice (the dedup vs `ry-sync-reminder` is intentional).

## What we do not use

- **`auth` / `provider`** - Anthropic provider auto-loads via `opencode auth`. No need to register custom providers.
- **`chat.message` / `chat.params` / `chat.headers`** - current agent frontmatter already sets temperature/steps per agent; the pipeline hooks would be useful only if we needed dynamic per-message logic.
- **`experimental.chat.messages.transform`** - full message-history rewriting is not currently needed.
- **`experimental.text.complete`** - no post-processing of LLM output needed.
- **`experimental_workspace`** - single local workspace; no remote / distributed setup.

These are documented here as known surfaces in case future requirements warrant adopting them.

## CLI surfaces the marketplace can drive

Plugin code is not the only extension point. The OpenCode CLI exposes scriptable surfaces consumed in `docs/release-process.md`, `docs/dependency-updates.md`, `docs/rollback-restore.md`, and our reviewer/post-task-sync workflows:

- `opencode debug config | agent <name> | skill | info | startup | paths` - authoritative resolved state.
- `opencode models <provider>` - list valid model IDs for a provider.
- `opencode run "..."` - non-interactive prompt execution (useful for CI smoke tests of skills).
- `opencode export <sessionID>` / `opencode import <file>` - session portability.
- `opencode stats` - token/cost analytics for release-time review.
- `opencode session` - list / delete stored sessions.
- `opencode github` / `opencode pr <number>` - GitHub agent and PR-branch workflow.
- `opencode serve` / `opencode web` / `opencode acp` - headless server modes for distributed deployments.
- `opencode plugin <module>` - install plugin and update config (alias `opencode plug`).

None of these are wired into automation yet - they are available primitives.
