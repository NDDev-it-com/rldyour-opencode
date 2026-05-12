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

async function readMcpNames(projectDir: string): Promise<string[]> {
  try {
    const path = projectDir.endsWith("/") ? `${projectDir}opencode.json` : `${projectDir}/opencode.json`
    const raw = await Bun.file(path).text()
    const cfg = JSON.parse(raw) as { mcp?: Record<string, { enabled?: boolean }> }
    const mcp = cfg.mcp ?? {}
    return Object.keys(mcp).filter((name) => mcp[name]?.enabled !== false).sort()
  } catch {
    return []
  }
}

export const RyBootstrap: Plugin = async (ctx) => {
  const project = (ctx as { project?: { name?: string; path?: string } }).project
  const directory = (ctx as { directory?: string }).directory
  const projectName = project?.name ?? "unknown"
  const projectDir = project?.path ?? directory ?? "."

  return {
    event: async ({ event }) => {
      if (event.type === "session.created") {
        console.log(`[rldyour] Session started for project: ${projectName}`)
        console.log("[rldyour] Run /ry-init to bootstrap context, /ry-start for full task lifecycle.")
      }
    },

    "experimental.session.compacting": async (_input, output) => {
      const mcpNames = await readMcpNames(projectDir)
      const mcpLine =
        mcpNames.length > 0
          ? `Available MCP servers: ${mcpNames.join(", ")}`
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
