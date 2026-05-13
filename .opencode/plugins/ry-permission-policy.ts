import type { Plugin } from "@opencode-ai/plugin"

// Dynamic permission policy. Fires only when the static permission config
// (in opencode.json or per-agent frontmatter) sets a slot to "ask" — for
// "allow" / "deny" the runtime never calls this hook. The marketplace
// keeps the global build permissions at "allow" but the plan / reviewer
// subagents bump bash and edit to "ask"; this plugin tightens those by
// blocking categorically dangerous patterns before the user prompt even
// appears, so an accidental "allow" click cannot silently run them.
//
// IMPORTANT: this plugin only DENIES. It never auto-allows. The user's
// interactive consent on legitimate "ask" prompts is preserved verbatim —
// auto-allowing through `permission.ask` would bypass the central access
// control of OpenCode, which is unsafe to ship in a marketplace.
//
// Source: SDK Permission shape in dist/gen/types.gen.d.ts; hook contract
// in @opencode-ai/plugin dist/index.d.ts ("permission.ask").

export const RyPermissionPolicy: Plugin = async ({ client }) => {
  async function log(level: "warn" | "error", message: string): Promise<void> {
    try {
      await client.app.log({ body: { service: "ry-permission-policy", level, message } })
    } catch {
      // server log unavailable; carry on
    }
  }

  async function toast(message: string): Promise<void> {
    try {
      await client.tui.showToast({ body: { variant: "error", message } })
    } catch {
      // tui unavailable; carry on
    }
  }

  function commandFromPermission(input: { title: string; metadata: { [k: string]: unknown } }): string {
    const meta = input.metadata
    if (typeof meta?.command === "string") return meta.command
    if (typeof meta?.script === "string") return meta.script
    return input.title || ""
  }

  return {
    "permission.ask": async (input, output) => {
      if (input.type !== "bash") return

      const cmd = commandFromPermission(input)

      // Force push without lease — data-loss risk on shared branches.
      if (/\bgit\s+push\b/i.test(cmd) && /\b--force\b/.test(cmd) && !/\b--force-with-lease\b/.test(cmd)) {
        output.status = "deny"
        const message = "Denied git push --force without --force-with-lease (data-loss risk on shared branches)."
        await toast(message)
        await log("error", `${message} cmd=${cmd.slice(0, 200)}`)
        return
      }

      // rm -rf with root, home, or shell-relative root targets.
      // Allowlist `node_modules` because that is a common, safe cleanup.
      if (/\brm\s+(-rf?|-fr|--recursive)\b/i.test(cmd)) {
        const dangerous =
          /\brm\s+(-rf?|-fr|--recursive)\s+\/\s*$/i.test(cmd) ||
          /\brm\s+(-rf?|-fr|--recursive)\s+\$HOME\b/i.test(cmd) ||
          /\brm\s+(-rf?|-fr|--recursive)\s+~\/?\s*$/i.test(cmd) ||
          /\brm\s+(-rf?|-fr|--recursive)\s+\.\s*$/i.test(cmd)
        const isNodeModulesCleanup = /\brm\s+(-rf?|-fr|--recursive)\s+\S*\/?node_modules\/?\s*$/i.test(cmd)
        if (dangerous && !isNodeModulesCleanup) {
          output.status = "deny"
          const message = "Denied catastrophic rm -rf target (root/home/cwd)."
          await toast(message)
          await log("error", `${message} cmd=${cmd.slice(0, 200)}`)
          return
        }
      }

      // git push to product branch with --no-verify — bypasses pre-push
      // hooks the owner installed to keep release branches clean.
      if (/\bgit\s+push\b/i.test(cmd) && /\b--no-verify\b/.test(cmd) && /\bmain|master|release|production\b/i.test(cmd)) {
        output.status = "deny"
        const message = "Denied git push --no-verify on a product branch (pre-push hook bypass)."
        await toast(message)
        await log("error", `${message} cmd=${cmd.slice(0, 200)}`)
        return
      }

      // Everything else keeps the default "ask" so the user stays in control.
    },
  }
}
