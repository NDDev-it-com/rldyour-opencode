import type { Plugin } from "@opencode-ai/plugin"

// Conventional Commits advice on `git commit` is owned by ry-flow-hooks.ts.
// This plugin only handles the idle-session reminder.
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
  }
}
