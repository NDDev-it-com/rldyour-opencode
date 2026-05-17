import type { Plugin } from "@opencode-ai/plugin"

const STATIC_REVIEWERS = [
  "@flow-architecture-review",
  "@flow-quality-review",
  "@flow-consistency-review",
  "@flow-integration-review",
  "@flow-verification-review",
  "@flow-security-review",
]

declare const Bun: {
  file: (path: string) => { text: () => Promise<string> }
}

async function readMcpNames(projectDir: string): Promise<{ names: string[]; warning?: string }> {
  try {
    const path = projectDir.endsWith("/") ? `${projectDir}opencode.json` : `${projectDir}/opencode.json`
    const raw = await Bun.file(path).text()
    const cfg = JSON.parse(raw) as { mcp?: Record<string, { enabled?: boolean }> }
    const mcp = cfg.mcp ?? {}
    return { names: Object.keys(mcp).filter((name) => mcp[name]?.enabled !== false).sort() }
  } catch (err) {
    return {
      names: [],
      warning: `ry-bootstrap: could not read opencode.json (${err instanceof Error ? err.message : String(err)}). MCP list will be reported as unavailable.`,
    }
  }
}

export const RyBootstrap: Plugin = async ({ client, project, directory }) => {
  // Project type per @opencode-ai/sdk (gen/types.gen.d.ts) exposes
  // { id, worktree, vcsDir?, vcs?, time }. Neither `name` nor `path`
  // are typed fields — they were hand-rolled casts in earlier versions.
  // Use the typed `worktree` for the project directory and derive a
  // human-readable name from its basename.
  const projectDir = project?.worktree ?? directory ?? "."
  const projectName = projectDir.split("/").filter(Boolean).pop() ?? "unknown"

  async function log(level: "info" | "warn", message: string): Promise<void> {
    try {
      await client.app.log({ body: { service: "ry-bootstrap", level, message } })
    } catch {
      // server log unavailable; carry on
    }
  }

  return {
    event: async ({ event }) => {
      if (event.type === "session.created") {
        await log(
          "info",
          `session started for project: ${projectName}. Run /ry-init to bootstrap context, /ry-start for full task lifecycle.`,
        )
      }
    },

    // Disable the synthetic "continue" turn that OpenCode injects after a
    // context-overflow auto-compaction. Reviewer / security / sync agents
    // typically produce a final report; an auto-continue turn would either
    // re-do the work or generate empty filler. Letting the user (or the
    // orchestrating skill) choose the next prompt avoids both pitfalls.
    "experimental.compaction.autocontinue": async (input, output) => {
      if (input.overflow) {
        output.enabled = false
        await log("info", `compaction.autocontinue disabled for session ${input.sessionID.slice(0, 12)} (overflow)`)
      }
    },

    "experimental.session.compacting": async (_input, output) => {
      const { names, warning } = await readMcpNames(projectDir)
      if (warning) {
        await log("warn", warning)
      }
      const mcpLine =
        names.length > 0
          ? `Available MCP servers: ${names.join(", ")}`
          : "Available MCP servers: (read opencode.json for current list)"

      output.context.push(`## rldyour Session Context (${projectName})
Project: ${projectName} at ${projectDir}
Workflow: /ry-init → /ry-start → /ry-sync at end
${mcpLine}
Available reviewer subagents: ${STATIC_REVIEWERS.join(", ")}
Deep research: @ry-explore for multi-source research with Context7, DeepWiki, Grep
Communication: Russian by default unless explicitly requested otherwise
Rules: quality-first, no hacks, no swallowed errors, conventional commits, atomic per logical unit
Always run /ry-sync before ending a session to synchronize memories, docs, and git state.`)
    },
  }
}
