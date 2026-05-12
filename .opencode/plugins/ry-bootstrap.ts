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
Project: ${projectName} at ${projectDir}
Workflow: /ry-init → /ry-start → /ry-sync at end
Available MCP servers: serena, sequential-thinking, playwright, chrome-devtools, context7, deepwiki, grep, semgrep, shadcn, dart-flutter, figma, github, openai-docs
Available reviewer subagents: @flow-architecture-review, @flow-quality-review, @flow-consistency-review, @flow-integration-review, @flow-verification-review, @flow-security-review
Deep research: @ry-explore for multi-source research with Context7, DeepWiki, Grep
Communication: Russian by default unless explicitly requested otherwise
Rules: quality-first, no hacks, no swallowed errors, conventional commits, atomic per logical unit
Always run /ry-sync before ending a session to synchronize memories, docs, and git state.`)
    },
  }
}