import type { Plugin } from "@opencode-ai/plugin"

// User-visible messaging uses OpenCode v1.14.48 client API:
//   client.app.log({ body: { service, level, message }})  → server log file
//   client.tui.showToast({ body: { variant, message }})  → toast banner in TUI
// console.log only reaches the server log file and is invisible to the
// user, so warnings that the user must see are escalated to toasts.
// Each notify call is wrapped in try/catch — best-effort UX: messaging
// failures must never block tool execution.
//
// Defense-in-depth: this plugin's `tool.execute.before` throw is the
// UNCONDITIONAL enforcement layer for git push hardening. It fires
// regardless of whether the bash permission is "allow" or "ask".
// `ry-permission-policy.ts` provides the secondary layer at
// `permission.ask`, which catches the same patterns before the user
// dialog appears — only relevant when bash is statically "ask"
// (plan agent + reviewer subagents). Both layers intentionally co-own
// the same invariant; removing either creates a coverage gap.

export const RyShellStrategy: Plugin = async ({ client }) => {
  async function log(level: "info" | "warn" | "error", message: string): Promise<void> {
    try {
      await client.app.log({ body: { service: "ry-shell-strategy", level, message } })
    } catch {
      // server log unavailable; carry on
    }
  }

  async function toast(variant: "info" | "warning" | "error", message: string): Promise<void> {
    try {
      await client.tui.showToast({ body: { variant, message } })
    } catch {
      // tui unavailable; carry on
    }
  }

  return {
    "shell.env": async (_input, output) => {
      output.env.GIT_TERMINAL_PROMPT = "0"
      output.env.CI = "1"
      output.env.NODE_OPTIONS = "--max-old-space-size=4096"
    },

    "tool.execute.before": async (input, output) => {
      if (input.tool !== "bash") return
      const command: string = output.args?.command ?? ""

      // Flag-boundary helpers: `\b` does NOT match between two non-word
      // chars (space and `-`), so the naive `\b--FLAG\b` form silently
      // fails. Use a negated alphanum-or-hyphen lookbehind/lookahead so
      // `--force` matches but `--force-with-lease` does not. Same logic
      // for `--no-verify`. Mirrors ry-permission-policy.ts.
      const FLAG_BOUNDARY_PRE = "(?<![A-Za-z0-9-])"
      const FLAG_BOUNDARY_POST = "(?![A-Za-z0-9-])"
      const longForce = new RegExp(`${FLAG_BOUNDARY_PRE}--force${FLAG_BOUNDARY_POST}`, "i")
      const lease = new RegExp(`${FLAG_BOUNDARY_PRE}--force-with-lease${FLAG_BOUNDARY_POST}`, "i")
      const noVerify = new RegExp(`${FLAG_BOUNDARY_PRE}--no-verify${FLAG_BOUNDARY_POST}`, "i")
      const shortForce = /(?:^|\s)-f(?:\s|$)/

      const isPush = /\bgit\s+push\b/i.test(command)

      if (isPush && !noVerify.test(command)) {
        await toast("warning", "git push: run quality gates and /ry-sync first")
        await log(
          "info",
          "git push detected — recommend running tests/type checks, Serena memory sync, and conventional commit verification before push",
        )
      }

      if (isPush && (longForce.test(command) || shortForce.test(command)) && !lease.test(command)) {
        const msg = "Blocked git push --force / -f without --force-with-lease (data-loss risk)."
        await toast("error", msg)
        throw new Error(`[rldyour] ${msg} Use --force-with-lease for safer force pushes.`)
      }

      if (/\brm\s+(-rf?|--recursive)\s+.*\//i.test(command) && !/\/node_modules\/?$/i.test(command)) {
        await toast("warning", "Destructive rm command detected — verify target before proceeding.")
        await log("warn", `destructive rm command: ${command.slice(0, 200)}`)
      }
    },
  }
}
