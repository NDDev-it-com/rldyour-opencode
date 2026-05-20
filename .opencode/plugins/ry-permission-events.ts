import type { Plugin } from "@opencode-ai/plugin"

// Permission enforcement intentionally does NOT live here.
//
// OpenCode v1.15.4's plugin SDK still exposes a `permission.ask` hook type,
// but source/runtime inspection shows the permission service publishes
// `permission.asked` / `permission.replied` bus events and does not trigger
// a plugin-level `permission.ask` hook. Treating that typed-but-untriggered
// hook as a security boundary creates false confidence.
//
// Dynamic denial stays in `ry-shell-strategy.ts` via `tool.execute.before`,
// which is triggered before the bash tool executes regardless of static
// permission mode. This plugin is observability-only: it records permission
// prompts and replies seen on the documented event stream.

type PermissionEvent = {
  type?: string
  properties?: Record<string, unknown>
}

function short(value: unknown): string {
  return typeof value === "string" && value ? value.slice(0, 12) : "unknown"
}

function text(value: unknown): string {
  return typeof value === "string" && value ? value : "unknown"
}

export const RyPermissionEvents: Plugin = async ({ client }) => {
  async function log(level: "info" | "warn", message: string): Promise<void> {
    try {
      await client.app.log({ body: { service: "ry-permission-events", level, message } })
    } catch {
      // server log unavailable; carry on
    }
  }

  return {
    event: async ({ event }) => {
      const observed = event as PermissionEvent
      if (observed.type !== "permission.asked" && observed.type !== "permission.replied") return

      const props = observed.properties ?? {}
      if (observed.type === "permission.asked") {
        await log(
          "info",
          `permission asked: session=${short(props.sessionID)} request=${short(props.id)} permission=${text(props.permission)}`,
        )
        return
      }

      await log(
        "info",
        `permission replied: session=${short(props.sessionID)} request=${short(props.requestID)} reply=${text(props.reply)}`,
      )
    },
  }
}
