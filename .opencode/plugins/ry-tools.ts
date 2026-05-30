/**
 * Multi-domain diagnostic aggregator.
 *
 * Tools registered here span multiple domains from AGENTS.md § Domain
 * Boundaries — Flow (validate_config, git_audit, fullrepo_status),
 * LSP (lsp_health), Dependency (check_deps). Bundling is intentional:
 * the plugin only *exposes* diagnostic scripts; the scripts themselves
 * stay within their respective domains. New tools added here MUST:
 *   1. Wrap an existing script under scripts/ (no in-plugin business logic).
 *   2. Pass args: {} (no user input flows into the spawn argv).
 *   3. Be documented in AGENTS.md plugin block + CHANGELOG.
 *   4. Have a tool ID prefixed `rldyour_` to keep namespace clean.
 */
import type { Plugin, ToolDefinition } from "@opencode-ai/plugin"
import { tool } from "@opencode-ai/plugin"

declare const Bun: {
  spawn: (
    cmd: string[],
    opts?: { cwd?: string; stdout?: "pipe" | "inherit"; stderr?: "pipe" | "inherit" },
  ) => {
    exited: Promise<number>
    stdout: ReadableStream
    stderr: ReadableStream
    kill: (signal?: number | string) => void
  }
}

// Per-tool timeouts/output caps. Without these, a hung diagnostic script
// (e.g., a locked git index, a slow MCP probe, a stale Bun cache) can wedge
// the LLM tool call indefinitely. doctor_opencode.sh did this in audit
// snapshots — keep the cap strict and surface the structured timeout reason
// in the tool output, not a raw hang. maxOutputBytes also protects the LLM
// context window from being flooded by a chatty script.
type ScriptResult = {
  exitCode: number
  stdout: string
  stderr: string
  timedOut: boolean
  truncated: boolean
}

async function runScript(
  cwd: string,
  args: string[],
  opts: { timeoutMs: number; maxOutputBytes: number },
): Promise<ScriptResult> {
  const { timeoutMs, maxOutputBytes } = opts
  let timedOut = false
  let proc: ReturnType<typeof Bun.spawn> | undefined
  const timer = setTimeout(() => {
    timedOut = true
    try {
      proc?.kill()
    } catch {
      // process may have already exited
    }
  }, timeoutMs)
  try {
    proc = Bun.spawn(args, { cwd, stdout: "pipe", stderr: "pipe" })
    const [rawStdout, rawStderr] = await Promise.all([
      new Response(proc.stdout).text(),
      new Response(proc.stderr).text(),
    ])
    const exitCode = await proc.exited
    const stdoutTruncated = rawStdout.length > maxOutputBytes
    const stderrTruncated = rawStderr.length > maxOutputBytes
    return {
      exitCode,
      stdout: stdoutTruncated ? rawStdout.slice(0, maxOutputBytes) : rawStdout,
      stderr: stderrTruncated ? rawStderr.slice(0, maxOutputBytes) : rawStderr,
      timedOut,
      truncated: stdoutTruncated || stderrTruncated,
    }
  } finally {
    clearTimeout(timer)
  }
}

function formatTimeoutResult(toolId: string, timeoutMs: number): string {
  return [
    `[TIMEOUT] ${toolId} did not finish within ${timeoutMs}ms.`,
    "The underlying script likely hangs on filesystem, MCP, or git state.",
    `Hint: invoke the wrapped script directly (with --json when supported) to narrow diagnosis.`,
  ].join("\n")
}

// Per-tool budgets. Each LLM-callable diagnostic gets a strict total deadline
// and an output cap so a single hung script cannot wedge the tool call. Keep
// the values aligned with the worst-case wall time the wrapped scripts can
// take on a healthy machine; doctor and smoke probe MCP servers, so they get
// the largest budgets. Updating these together with the script behavior keeps
// the LLM's expectations and the runtime in lockstep.
const TOOL_BUDGETS = {
  validateConfig: { timeoutMs: 30_000, maxOutputBytes: 256_000 },
  checkDeps: { timeoutMs: 30_000, maxOutputBytes: 64_000 },
  lspHealth: { timeoutMs: 20_000, maxOutputBytes: 128_000 },
  gitAudit: { timeoutMs: 15_000, maxOutputBytes: 64_000 },
  fullrepoStatus: { timeoutMs: 15_000, maxOutputBytes: 64_000 },
} as const

function buildTools(getCwd: () => string): Record<string, ToolDefinition> {
  return {
    rldyour_validate_config: tool({
      description:
        "Запускает `bash scripts/validate_config.sh` для активного проекта. EN: returns validator output verbatim and fails non-zero on any issue; use before delivery to confirm opencode.json, skills, agents, commands, and VERSION.",
      args: {},
      async execute(_args, ctx) {
        const cwd = ctx.directory || getCwd()
        const budget = TOOL_BUDGETS.validateConfig
        const result = await runScript(cwd, ["bash", "scripts/validate_config.sh"], budget)
        if (result.timedOut) {
          ctx.metadata({ title: "validate TIMEOUT", metadata: { timeoutMs: budget.timeoutMs } })
          return formatTimeoutResult("validate_config.sh", budget.timeoutMs)
        }
        const output = result.exitCode === 0
          ? `[OK] validate_config exit 0\n\n${result.stdout}`
          : `[FAIL] validate_config exit ${result.exitCode}\n\nstdout:\n${result.stdout}\n\nstderr:\n${result.stderr}`
        ctx.metadata({
          title: result.exitCode === 0 ? "validate ok" : "validate FAIL",
          metadata: { exitCode: result.exitCode, truncated: result.truncated },
        })
        return output
      },
    }),

    rldyour_check_deps: tool({
      description:
        "Проверяет свежесть pinned MCP dependencies через `bash scripts/check_deps_freshness.sh --json`. EN: returns JSON for npm/bunx, PyPI/uvx, and Dart SDK pins; use for version review or bumps.",
      args: {},
      async execute(_args, ctx) {
        const cwd = ctx.directory || getCwd()
        const budget = TOOL_BUDGETS.checkDeps
        const result = await runScript(cwd, ["bash", "scripts/check_deps_freshness.sh", "--json"], budget)
        if (result.timedOut) {
          ctx.metadata({ title: "deps TIMEOUT", metadata: { timeoutMs: budget.timeoutMs } })
          return formatTimeoutResult("check_deps_freshness.sh", budget.timeoutMs)
        }
        ctx.metadata({
          title: "deps pins",
          metadata: { exitCode: result.exitCode, truncated: result.truncated },
        })
        if (result.exitCode !== 0) {
          return `[FAIL] check_deps_freshness exit ${result.exitCode}\nstderr:\n${result.stderr}`
        }
        return result.stdout
      },
    }),

    rldyour_lsp_health: tool({
      description:
        "Проверяет health language servers через `bash scripts/check_lsps.sh`. EN: reports PATH availability and project prereqs such as pyproject.toml, tsconfig, or Cargo.toml for LSP diagnostics.",
      args: {},
      async execute(_args, ctx) {
        const cwd = ctx.directory || getCwd()
        const budget = TOOL_BUDGETS.lspHealth
        const result = await runScript(cwd, ["bash", "scripts/check_lsps.sh"], budget)
        if (result.timedOut) {
          ctx.metadata({ title: "lsp TIMEOUT", metadata: { timeoutMs: budget.timeoutMs } })
          return formatTimeoutResult("check_lsps.sh", budget.timeoutMs)
        }
        ctx.metadata({
          title: "lsp health",
          metadata: { exitCode: result.exitCode, truncated: result.truncated },
        })
        return `exit=${result.exitCode}\n\n${result.stdout}${result.stderr ? `\n\nstderr:\n${result.stderr}` : ""}`
      },
    }),

    rldyour_git_audit: tool({
      description:
        "Аудит git state через `bash scripts/git_sync_audit.sh`. EN: reports branch, upstream, dirty files, worktrees, and merged-branch cleanup candidates before git operations or /ry-sync.",
      args: {},
      async execute(_args, ctx) {
        const cwd = ctx.directory || getCwd()
        const budget = TOOL_BUDGETS.gitAudit
        const result = await runScript(cwd, ["bash", "scripts/git_sync_audit.sh"], budget)
        if (result.timedOut) {
          ctx.metadata({ title: "git audit TIMEOUT", metadata: { timeoutMs: budget.timeoutMs } })
          return formatTimeoutResult("git_sync_audit.sh", budget.timeoutMs)
        }
        ctx.metadata({
          title: "git audit",
          metadata: { exitCode: result.exitCode, truncated: result.truncated },
        })
        return result.stdout || result.stderr
      },
    }),

    rldyour_fullrepo_status: tool({
      description:
        "Проверяет fullrepo state через `bash scripts/fullrepo_sync.sh status-json`. EN: returns JSON for agent-only branch, dirty/ahead/behind state, fullrepo existence, and Serena memory count before /ry-sync.",
      args: {},
      async execute(_args, ctx) {
        const cwd = ctx.directory || getCwd()
        const budget = TOOL_BUDGETS.fullrepoStatus
        const result = await runScript(cwd, ["bash", "scripts/fullrepo_sync.sh", "status-json"], budget)
        if (result.timedOut) {
          ctx.metadata({ title: "fullrepo TIMEOUT", metadata: { timeoutMs: budget.timeoutMs } })
          return formatTimeoutResult("fullrepo_sync.sh status-json", budget.timeoutMs)
        }
        ctx.metadata({
          title: "fullrepo status",
          metadata: { exitCode: result.exitCode, truncated: result.truncated },
        })
        return result.stdout || result.stderr
      },
    }),
  }
}

export const RyTools: Plugin = async ({ directory }) => {
  // PluginInput.directory is always defined per @opencode-ai/plugin v1.14
  // type contract (string, not nullable). Bind once at factory time.
  const getCwd = (): string => directory
  return {
    tool: buildTools(getCwd),
  }
}
