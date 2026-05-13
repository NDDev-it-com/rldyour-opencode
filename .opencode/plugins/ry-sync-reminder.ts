import type { Plugin } from "@opencode-ai/plugin"

// Conventional Commits advice on `git commit` is owned by ry-flow-hooks.ts.
// This plugin only handles the idle-session reminder via a toast (visible)
// + a single app.log line (audit-friendly).
export const RySyncReminder: Plugin = async ({ client }) => {
  return {
    event: async ({ event }) => {
      if (event.type !== "session.idle") return

      const message =
        "Session is idle — run /ry-sync to refresh Serena memories, docs, git state, and fullrepo before ending."

      try {
        await client.tui.showToast({ body: { variant: "info", message, duration: 8000 } })
      } catch {
        // tui unavailable; carry on
      }
      try {
        await client.app.log({ body: { service: "ry-sync-reminder", level: "info", message } })
      } catch {
        // server log unavailable; carry on
      }
    },
  }
}
