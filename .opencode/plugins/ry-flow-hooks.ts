import type { Plugin } from "@opencode-ai/plugin"

// Owner-visible commit advice for `tool.execute.after` on bash. Conventional
// Commits format check is owned exclusively by this plugin — ry-sync-reminder
// no longer subscribes to tool.execute.after to avoid duplicate output.
//
// Notify failures are silently swallowed so the LLM never sees an advisory
// plugin throw stop its own follow-up work.

const CC_TYPES = "feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert"
const CC_REGEX = new RegExp(`^(${CC_TYPES})(\\(.+\\))?:\\s.{10,}`, "m")

export const RyFlowHooks: Plugin = async ({ client }) => {
  async function log(level: "info" | "warn", message: string): Promise<void> {
    try {
      await client.app.log({ body: { service: "ry-flow-hooks", level, message } })
    } catch {
      // server log unavailable; carry on
    }
  }

  async function toast(variant: "info" | "warning", message: string): Promise<void> {
    try {
      await client.tui.showToast({ body: { variant, message } })
    } catch {
      // tui unavailable; carry on
    }
  }

  return {
    "tool.execute.after": async (input, output) => {
      if (input.tool !== "bash") return
      const command: string = (output as { args?: { command?: string } }).args?.command ?? ""
      const resultText: string =
        typeof output.output === "string"
          ? output.output
          : output.output != null
            ? String(output.output)
            : ""

      if (/\bgit\s+commit\b/i.test(command)) {
        if (!CC_REGEX.test(resultText)) {
          await toast(
            "warning",
            `Commit not in Conventional Commits format (${CC_TYPES.replace(/\|/g, "/")})`,
          )
          await log("warn", "non-conventional commit subject detected on git commit output")
        }
      }

      if (/\bgit\s+(commit|merge|cherry-pick|rebase)\b/i.test(command) && !/\b--amend\b/.test(command)) {
        if (resultText.includes("changed")) {
          await toast("info", "Repo changed — consider /ry-sync to refresh Serena memories and docs.")
          await log("info", "post-commit nudge: /ry-sync recommended")
        }
      }
    },
  }
}
