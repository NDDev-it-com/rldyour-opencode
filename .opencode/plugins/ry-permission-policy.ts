import type { Plugin } from "@opencode-ai/plugin"

// Plugin tsconfig keeps `types: []` to stay off @types/node; declare the
// process surface we actually consume so the RY_ALLOW_NO_VERIFY opt-out
// env check type-checks.
declare const process: { env: Record<string, string | undefined> }

// Dynamic permission policy. Fires only when the static permission config
// (in opencode.json or per-agent frontmatter) sets a slot to "ask" — for
// "allow" / "deny" the runtime never calls this hook. The marketplace
// keeps the global build permissions at "allow" but the plan / reviewer
// subagents bump bash and edit to "ask"; this plugin tightens those by
// blocking categorically dangerous patterns BEFORE the interactive
// permission dialog appears, so an accidental "allow" click cannot
// silently approve them.
//
// Defense-in-depth note: `ry-shell-strategy.ts` already throws on the
// same force-push pattern via `tool.execute.before`, which fires
// regardless of permission config. That throw is the unconditional
// enforcement layer. This plugin is the secondary guard for the
// `permission.ask` promotion path (plan agent + reviewer subagents).
// The two layers intentionally co-own the invariant so that:
//   - the global `"allow"` case is still blocked by ry-shell-strategy
//   - the `"ask"` case is blocked BEFORE the user dialog by this plugin
// Removing either layer would create a coverage gap.
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
      //
      // Regex boundary note: `\b` does NOT match between two non-word
      // characters (space and `-`). The naive `\b--force\b` therefore
      // never fires on `git push --force` because the leading `\b`
      // tries to assert at the space-dash transition. Use a negated
      // alphanum-or-hyphen lookbehind/lookahead instead — that lets
      // `--force` match while excluding `--force-with-lease` (next
      // char is `-`, which is in the class).
      const FLAG_BOUNDARY_PRE = "(?<![A-Za-z0-9-])"
      const FLAG_BOUNDARY_POST = "(?![A-Za-z0-9-])"
      const longForce = new RegExp(`${FLAG_BOUNDARY_PRE}--force${FLAG_BOUNDARY_POST}`, "i")
      const lease = new RegExp(`${FLAG_BOUNDARY_PRE}--force-with-lease${FLAG_BOUNDARY_POST}`, "i")
      const noVerify = new RegExp(`${FLAG_BOUNDARY_PRE}--no-verify${FLAG_BOUNDARY_POST}`, "i")

      const isPush = /\bgit\s+push\b/i.test(cmd)
      const hasLongForce = longForce.test(cmd)
      const hasShortForce = /(?:^|\s)-f(?:\s|$)/.test(cmd)
      const hasLease = lease.test(cmd)
      if (isPush && (hasLongForce || hasShortForce) && !hasLease) {
        output.status = "deny"
        const message = "Denied git push --force / -f without --force-with-lease (data-loss risk on shared branches)."
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
          /\brm\s+(-rf?|-fr|--recursive)\s+\.\s*$/i.test(cmd) ||
          // Parent-dir traversal: `rm -rf ..` from any project subdirectory
          // erases the entire project tree. Mirrors ry-shell-strategy.ts
          // Layer 1; reviewer wave 2026-05-18 security F-1 closure.
          /\brm\s+(-rf?|-fr|--recursive)\s+\.\.\/?\s*$/i.test(cmd)
        const isNodeModulesCleanup = /\brm\s+(-rf?|-fr|--recursive)\s+\S*\/?node_modules\/?\s*$/i.test(cmd)
        if (dangerous && !isNodeModulesCleanup) {
          output.status = "deny"
          const message = "Denied catastrophic rm -rf target (root/home/cwd)."
          await toast(message)
          await log("error", `${message} cmd=${cmd.slice(0, 200)}`)
          return
        }
      }

      // git push --no-verify. Audit Phase 1 + architecture-review F-1
      // widened both this secondary deny layer and the unconditional
      // Layer 1 in ry-shell-strategy.ts to block every --no-verify push
      // by default. The previous product-branch gate (main/master/release/
      // production) could be bypassed by `git push --no-verify origin HEAD`
      // when the CURRENT branch happens to be a product branch — no token
      // on the command line. The opt-out is the same RY_ALLOW_NO_VERIFY=1
      // env var honoured by Layer 1; setting it suppresses the auto-deny
      // here too, so the user keeps the interactive dialog choice. The
      // branchAlt regex is preserved to discriminate the audit-log signal
      // (product-branch attempt vs feature-branch attempt) with the same
      // block applied to both. ADR-006 defense-in-depth requires this
      // layer mirror the Layer 1 pattern coverage.
      const branchAlt = /\b(main|master|release|production)\b/i
      if (isPush && noVerify.test(cmd)) {
        if (process.env.RY_ALLOW_NO_VERIFY !== "1") {
          output.status = "deny"
          const productBranch = branchAlt.test(cmd)
          const message = productBranch
            ? "Denied git push --no-verify (pre-push hook bypass on a product branch)."
            : "Denied git push --no-verify (pre-push hook bypass)."
          await toast(message)
          await log("error", `${message} cmd=${cmd.slice(0, 200)}`)
          return
        }
        await log(
          "warn",
          `RY_ALLOW_NO_VERIFY=1 override active in permission.ask layer; user-dialog kept. cmd=${cmd.slice(0, 200)}`,
        )
      }

      // Everything else keeps the default "ask" so the user stays in control.
    },
  }
}
