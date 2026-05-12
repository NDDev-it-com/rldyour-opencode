import type { Plugin } from "@opencode-ai/plugin"

export const RyBootstrap: Plugin = async ({ project }) => {
  const projectName = project?.name ?? "unknown"
  const projectDir = project?.path ?? "."

  return {
    event: async ({ event }) => {
      if (event.type === "session.created") {
        console.log(`[rldyour] Session started for project: ${projectName}`)
        console.log("[rldyour] Run /ry-init to bootstrap context, /ry-start for full task lifecycle.")
      }
    },

    "experimental.session.compacting": async (input, output) => {
      output.context.push(`## rldyour Session Context (${projectName})
Key facts to preserve:
- Project: ${projectName} at ${projectDir}
- Workflow: /ry-init → /ry-start → /ry-sync at end
- Serena MCP available for symbol-level code navigation
- Reviewer subagents available: architecture, quality, consistency, integration, verification, security
- Always run /ry-sync before ending a session to synchronize memories, docs, and git state.
- Communication language: Russian by default unless explicitly requested otherwise.
- Engineering rules: quality-first, no hacks, no swallowed errors, conventional commits, atomic per logical unit.`)
    },
  }
}