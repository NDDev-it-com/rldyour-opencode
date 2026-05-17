import type { Plugin } from "@opencode-ai/plugin"

// Owner-visible commit advice for `tool.execute.after` on bash. Conventional
// Commits format check is owned exclusively by this plugin — ry-sync-reminder
// no longer subscribes to tool.execute.after to avoid duplicate output.
//
// Notify failures are silently swallowed so the LLM never sees an advisory
// plugin throw stop its own follow-up work.
//
// SDK contract per @opencode-ai/plugin@1.15.4 dist/index.d.ts:
//   "tool.execute.after"?: (
//     input:  { tool: string; sessionID: string; callID: string; args: any },
//     output: { title: string; output: string; metadata: any },
//   ) => Promise<void>
// IMPORTANT: bash args live on `input.args`, NOT `output.args`. Reading from
// output silently fails — the regex matchers never see the real command. Use
// the `getBashCommand` helper below so this never drifts again. Locked by
// `scripts/tests/test_plugin_surface.py::test_flow_hooks_reads_command_from_input`.

const CC_TYPES = "feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert"
const CC_REGEX = new RegExp(`^(${CC_TYPES})(\\(.+\\))?:\\s.{10,}`, "m")

function getBashCommand(input: { tool: string; args?: unknown }): string {
  if (input.tool !== "bash") return ""
  const args = input.args
  if (!args || typeof args !== "object") return ""
  const command = (args as Record<string, unknown>).command
  return typeof command === "string" ? command : ""
}

function getBashOutput(output: { output?: unknown }): string {
  const raw = output.output
  if (typeof raw === "string") return raw
  if (raw == null) return ""
  return String(raw)
}

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
      const command = getBashCommand(input)
      if (command === "") return
      const resultText = getBashOutput(output)

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
