import type { Plugin } from "@opencode-ai/plugin"

export const RyShellStrategy: Plugin = async ({ directory }) => {
  return {
    "shell.env": async (input, output) => {
      output.env.GIT_TERMINAL_PROMPT = "0"
      output.env.CI = "1"
      output.env.NODE_OPTIONS = "--max-old-space-size=4096"
    },

    "tool.execute.before": async (input, output) => {
      if (input.tool === "bash") {
        const command: string = output.args?.command ?? ""

        if (/\bgit\s+push\b/i.test(command) && !/\b--no-verify\b/.test(command)) {
          console.log("[rldyour] git push detected. Quality checklist:")
          console.log("  1. Run applicable tests and type checks")
          console.log("  2. Verify Serena memories are current (consider /ry-sync)")
          console.log("  3. Ensure conventional commits format")
        }

        if (/\bgit\s+push\s+--force\b/i.test(command) && !/\b--force-with-lease\b/.test(command)) {
          throw new Error(
            "[rldyour] Blocked git push --force. Use --force-with-lease instead for safer force pushes."
          )
        }

        if (/\brm\s+(-rf?|--recursive)\s+.*\//i.test(command) && !/\/node_modules\/?$/i.test(command)) {
          console.log("[rldyour] Warning: destructive rm command detected. Ensure target is correct.")
        }
      }
    },
  }
}