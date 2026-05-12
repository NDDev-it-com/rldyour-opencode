import type { Plugin } from "@opencode-ai/plugin"

export const RySyncReminder: Plugin = async () => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        console.log("[rldyour] ═════════════════════════════════════════════════════")
        console.log("[rldyour] Session is idle. Before ending:")
        console.log("[rldyour]   1. Run /ry-sync to synchronize memories, docs, and git state")
        console.log("[rldyour]   2. Verify all changes are committed with conventional commits")
        console.log("[rldyour]   3. Push to upstream if needed")
        console.log("[rldyour] ═════════════════════════════════════════════════════")
      }
    },

    "tool.execute.after": async (input, output) => {
      if (input.tool === "bash") {
        const command: string = output.args?.command ?? ""

        if (/\bgit\s+commit\b/i.test(command)) {
          const message: string = output.result?.toString() ?? ""
          const conventionalPattern = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?:\s.+/
          if (message && !conventionalPattern.test(message.split("\n")[0])) {
            console.log("[rldyour] Suggestion: Use Conventional Commits format:")
            console.log("[rldyour]   feat(scope): description")
            console.log("[rldyour]   fix(scope): description")
          }
        }
      }
    },
  }
}