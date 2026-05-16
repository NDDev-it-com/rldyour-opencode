# OpenCode Plugin Patterns

Reference for the advanced `@opencode-ai/plugin` hook surface used by this marketplace. Sourced from `.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts` v1.15.3 (pin updated from v1.14.48 — the runtime hook surface and tool-ID format are unchanged across these minors); cross-checked against https://opencode.ai/docs/plugins/.

## Plugin context

Every plugin factory receives:

```ts
PluginInput = {
  client: ReturnType<typeof createOpencodeClient>  // SDK client for server API
  project: Project                                 // { name, path, ... }
  directory: string                                // process working directory
  worktree: string                                 // git worktree root
  experimental_workspace: { register: (type, adapter) => void }
  serverUrl: URL
  $: BunShell                                      // Bun shell helper
}
```

Use `directory` (not `process.cwd()`) for relative paths. Cast `project as { name?, path? }` when you need those fields — they exist at runtime but the published `Project` type does not expose them in v1.14.

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
| `permission.ask` | Permission prompt | Override `status` to `"allow"` / `"deny"` (see security note below) |

> **Security note on `permission.ask`.** Setting `output.status = "allow"` unconditionally inside this hook bypasses the user's interactive consent — the central access control of OpenCode. Only use this hook with a precise, auditable allowlist condition (e.g., a narrow patterns array tied to a specific tool + sessionID). Never ship a plugin that auto-allows broadly. This repo's `ry-permission-policy.ts` subscribes to `permission.ask` in **deny-only mode**: it sets `output.status = "deny"` for categorically dangerous bash patterns (force-push without lease, catastrophic `rm -rf`, `--no-verify` on product branches) and never auto-allows. Legitimate "ask" prompts keep their user consent verbatim.

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

- `rldyour_validate_config` — runs `scripts/validate_config.sh`.
- `rldyour_check_deps` — runs `scripts/check_deps_freshness.sh --json`.
- `rldyour_lsp_health` — runs `scripts/check_lsps.sh`.
- `rldyour_git_audit` — runs `scripts/git_sync_audit.sh`.
- `rldyour_fullrepo_status` — runs `scripts/fullrepo_sync.sh status-json`.

Each tool returns the script's combined stdout/stderr and stamps `ctx.metadata({ title, metadata: { exitCode } })` so the TUI shows pass/fail at a glance.

### Slash-command audit (`.opencode/plugins/ry-command-audit.ts`)

`command.execute.before` appends one line per slash command invocation to `.serena/.command_audit.log` (runtime marker — never committed). Args are sanitized for credential-shaped patterns before logging. Log rotates with reset when it crosses 256 KiB.

### Tool routing nudges (`.opencode/plugins/ry-tool-hints.ts`)

`tool.definition` appends one short routing hint per known MCP tool ID. Hints encode the AGENTS.md tool-priority matrix (e.g., "Use Serena `find_symbol` before raw grep") so the LLM has the routing rule in the tool description itself, not just the high-level AGENTS.md instructions.

HINTS keys use the OpenCode `<server>_<tool>` tool-ID format (single underscore; dashes preserved; introduced in v1.14.48, unchanged through v1.15.3). Example: `serena_find_symbol`, `chrome-devtools_list_console_messages`, `context7_resolve-library-id`. The Claude-Code-style `mcp__server__tool` prefix silently disables every hint and is banned by `scripts/tests/test_plugin_surface.py::test_ry_tool_hints_no_legacy_aliases`.

### Permission policy (`.opencode/plugins/ry-permission-policy.ts`)

`permission.ask` deny-only policy. Fires only when the static permission config (in `opencode.json` or per-agent frontmatter) sets a slot to `"ask"` — for `"allow"` / `"deny"` the runtime never calls the hook. Blocks three categorically dangerous patterns before the interactive permission dialog appears:

- `git push --force` without `--force-with-lease` — data-loss risk on shared branches.
- `rm -rf <root|$HOME|~/|cwd>` — catastrophic; `node_modules` cleanup is allowlisted.
- `git push --no-verify` on `main` / `master` / `release` / `production` — pre-push hook bypass.

Never auto-allows; legitimate "ask" prompts keep user consent. Complements (not replaces) the unconditional `tool.execute.before` throws in `ry-shell-strategy.ts` — that one fires regardless of permission config; this one catches the same patterns when bash permission is statically `"ask"` (plan agent + reviewer subagents).

### Dynamic system prompt context (`.opencode/plugins/ry-system-context.ts`)

`experimental.chat.system.transform` injects a one-line runtime stamp into every system prompt: `[rldyour runtime] date=YYYY-MM-DD branch=... head=<short> worktree=clean|dirty(N files)`. Probes git via `Bun.spawn` with silent fallback ("unknown" when git unavailable). Branch and HEAD are session-stable and should ideally be cached at factory init; `git status --porcelain` is the only turn-volatile probe. Grounds the LLM in "now" facts that the static AGENTS.md cannot carry.

### Compaction autocontinue suppression (`.opencode/plugins/ry-bootstrap.ts`)

`experimental.compaction.autocontinue` sets `output.enabled = false` when `input.overflow` is true. The default synthetic "continue" turn after context-overflow compaction wastes tokens on reviewer / security / sync agents that already produced a final report. Letting the user (or orchestrating skill) choose the next prompt is cleaner than auto-generating filler.

### Observability: `client.app.log` + `client.tui.showToast`

All 10 plugins use the OpenCode v1.14.48+ (currently pinned at v1.15.3) client API for user-visible and structured logging instead of `console.log` (which lands only in the server log file `~/.local/share/opencode/log/*.log` and is invisible to the user):

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

Both helpers are best-effort — a transient client error never blocks the underlying tool execution. The `service` field per `client.app.log` matches the plugin file stem (`ry-shell-strategy`, `ry-flow-hooks`, etc.) for grep-friendly filtering. Toast `variant` set as `"warning"` for advisory, `"error"` for blocks; `"info"` only for low-frequency banners (idle reminder, post-commit `/ry-sync` nudge). Console.log is reserved for unit-test fixtures or temporary debugging — production plugins must not use it.

### Session bootstrap context (`.opencode/plugins/ry-bootstrap.ts`)

`event` (`session.created`) surfaces a one-line bootstrap message via `client.app.log` (not `console.log`). `experimental.session.compacting` injects the active MCP server list (read live from `opencode.json` via `Bun.file()`), reviewer subagent list, workflow sequence, and quality rules. The reviewer list is hardcoded (it is stable); the MCP list is dynamic.

### Sensitive-path guard (`.opencode/plugins/ry-env-protection.ts`)

`tool.execute.before` throws on reads / bash commands that touch `.env*`, `.pem`, `.key`, `.p12`, `.pfx`, `.ssh`, `.gnupg`, `.aws`, `secret`, `private_key`, `service_account` paths. Whitelist: `.env.example`, `.env.template`, `.env.sample`.

### Shell hardening (`.opencode/plugins/ry-shell-strategy.ts`)

`shell.env` injects non-interactive git/CI env (`GIT_TERMINAL_PROMPT=0`, `CI=1`, `NODE_OPTIONS=--max-old-space-size=4096`). `tool.execute.before` is the unconditional enforcement layer for git push: throws on `git push --force` without `--force-with-lease` (surfaces a `toast("error", ...)` before throwing), warns on destructive `rm -rf .../` (`toast("warning", ...)` + `log("warn", ...)`), and surfaces a quality checklist on `git push` as a toast. Defense-in-depth with `ry-permission-policy.ts` — that plugin also denies the same patterns at the `permission.ask` layer when bash is statically `"ask"`; the `tool.execute.before` throw here fires regardless of permission config.

### Session-idle reminder (`.opencode/plugins/ry-sync-reminder.ts`)

`event` filter on `session.idle` surfaces an end-of-session reminder via `client.tui.showToast` (8 s duration) plus one `client.app.log` line for the audit trail.

### Post-commit Conventional Commits advice (`.opencode/plugins/ry-flow-hooks.ts`)

`tool.execute.after` parses `git commit` output, checks the subject against the Conventional Commits regex, and surfaces format advice as a `toast("warning", ...)` on miss. Also nudges `/ry-sync` as a `toast("info", ...)` after `git commit|merge|cherry-pick|rebase`. Sole owner of post-commit advice (the dedup vs `ry-sync-reminder` is intentional).

## What we do not use

- **`auth` / `provider`** — Anthropic provider auto-loads via `opencode auth`. No need to register custom providers.
- **`chat.message` / `chat.params` / `chat.headers`** — current agent frontmatter already sets temperature/steps per agent; the pipeline hooks would be useful only if we needed dynamic per-message logic.
- **`experimental.chat.messages.transform`** — full message-history rewriting is not currently needed.
- **`experimental.text.complete`** — no post-processing of LLM output needed.
- **`experimental_workspace`** — single local workspace; no remote / distributed setup.

These are documented here as known surfaces in case future requirements warrant adopting them.

## CLI surfaces the marketplace can drive

Plugin code is not the only extension point. The OpenCode CLI exposes scriptable surfaces consumed in `docs/release-process.md`, `docs/dependency-updates.md`, `docs/rollback-restore.md`, and our reviewer/post-task-sync workflows:

- `opencode debug config | agent <name> | skill | info | startup | paths` — authoritative resolved state.
- `opencode models <provider>` — list valid model IDs for a provider.
- `opencode run "..."` — non-interactive prompt execution (useful for CI smoke tests of skills).
- `opencode export <sessionID>` / `opencode import <file>` — session portability.
- `opencode stats` — token/cost analytics for release-time review.
- `opencode session` — list / delete stored sessions.
- `opencode github` / `opencode pr <number>` — GitHub agent and PR-branch workflow.
- `opencode serve` / `opencode web` / `opencode acp` — headless server modes for distributed deployments.
- `opencode plugin <module>` — install plugin and update config (alias `opencode plug`).

None of these are wired into automation yet — they are available primitives.
