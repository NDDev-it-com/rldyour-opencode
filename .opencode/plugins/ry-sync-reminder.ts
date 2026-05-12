import type { Plugin } from "@opencode-ai/plugin"

export const RySyncReminder: Plugin = async () => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        console.log("[rldyour] Session is idle. Consider running /ry-sync to synchronize memories, docs, and git state before ending.")
      }
    },
  }
}