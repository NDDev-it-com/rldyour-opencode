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
          console.log("[rldyour] Note: git push detected. Ensure local quality checks pass before pushing.")
        }
      }
    },
  }
}