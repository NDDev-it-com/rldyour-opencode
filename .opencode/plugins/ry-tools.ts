import type { Plugin, ToolDefinition } from "@opencode-ai/plugin"
import { tool } from "@opencode-ai/plugin"

declare const Bun: {
  spawn: (cmd: string[], opts?: { cwd?: string; stderr?: "pipe" | "inherit" }) => {
    exited: Promise<number>
    stdout: ReadableStream
    stderr: ReadableStream
  }
}

async function runScript(cwd: string, args: string[]): Promise<{ exitCode: number; stdout: string; stderr: string }> {
  const proc = Bun.spawn(args, { cwd, stderr: "pipe" })
  const [stdout, stderr] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
  ])
  const exitCode = await proc.exited
  return { exitCode, stdout, stderr }
}

function buildTools(getCwd: () => string): Record<string, ToolDefinition> {
  return {
    rldyour_validate_config: tool({
      description:
        "Run `bash scripts/validate_config.sh` against the active project. Returns the validator output verbatim and exits non-zero on any failure. Use to confirm opencode.json, skills, agents, commands, and VERSION are schema-correct before delivery.",
      args: {},
      async execute(_args, ctx) {
        const cwd = ctx.directory || getCwd()
        const result = await runScript(cwd, ["bash", "scripts/validate_config.sh"])
        const output = result.exitCode === 0
          ? `[OK] validate_config exit 0\n\n${result.stdout}`
          : `[FAIL] validate_config exit ${result.exitCode}\n\nstdout:\n${result.stdout}\n\nstderr:\n${result.stderr}`
        ctx.metadata({ title: result.exitCode === 0 ? "validate ok" : "validate FAIL", metadata: { exitCode: result.exitCode } })
        return output
      },
    }),

    rldyour_check_deps: tool({
      description:
        "Run `bash scripts/check_deps_freshness.sh --json` and return the JSON envelope listing every pinned MCP dependency in opencode.json (npm via bunx, PyPI via uvx, Dart SDK). Use when reviewing or bumping versions.",
      args: {},
      async execute(_args, ctx) {
        const cwd = ctx.directory || getCwd()
        const result = await runScript(cwd, ["bash", "scripts/check_deps_freshness.sh", "--json"])
        ctx.metadata({ title: "deps pins", metadata: { exitCode: result.exitCode } })
        if (result.exitCode !== 0) {
          return `[FAIL] check_deps_freshness exit ${result.exitCode}\nstderr:\n${result.stderr}`
        }
        return result.stdout
      },
    }),

    rldyour_lsp_health: tool({
      description:
        "Run `bash scripts/check_lsps.sh` and return language-server health for the project (PATH availability + project prereqs like pyproject.toml, tsconfig, Cargo.toml). Use when diagnosing LSP-related issues.",
      args: {},
      async execute(_args, ctx) {
        const cwd = ctx.directory || getCwd()
        const result = await runScript(cwd, ["bash", "scripts/check_lsps.sh"])
        ctx.metadata({ title: "lsp health", metadata: { exitCode: result.exitCode } })
        return `exit=${result.exitCode}\n\n${result.stdout}${result.stderr ? `\n\nstderr:\n${result.stderr}` : ""}`
      },
    }),

    rldyour_git_audit: tool({
      description:
        "Run `bash scripts/git_sync_audit.sh` and return current branch, upstream, dirty files, worktrees, and merged-branch cleanup candidates. Use as a precursor to git operations or before /ry-sync.",
      args: {},
      async execute(_args, ctx) {
        const cwd = ctx.directory || getCwd()
        const result = await runScript(cwd, ["bash", "scripts/git_sync_audit.sh"])
        ctx.metadata({ title: "git audit", metadata: { exitCode: result.exitCode } })
        return result.stdout || result.stderr
      },
    }),

    rldyour_fullrepo_status: tool({
      description:
        "Run `bash scripts/fullrepo_sync.sh status-json` and return JSON describing the agent-only fullrepo branch state (branch, dirty, ahead/behind, fullrepo existence, Serena memory count). Use before /ry-sync to know whether fullrepo publish is needed.",
      args: {},
      async execute(_args, ctx) {
        const cwd = ctx.directory || getCwd()
        const result = await runScript(cwd, ["bash", "scripts/fullrepo_sync.sh", "status-json"])
        ctx.metadata({ title: "fullrepo status", metadata: { exitCode: result.exitCode } })
        return result.stdout || result.stderr
      },
    }),
  }
}

export const RyTools: Plugin = async ({ project, directory }) => {
  const proj = project as { path?: string } | undefined
  const getCwd = (): string => proj?.path ?? directory ?? "."
  return {
    tool: buildTools(getCwd),
  }
}
