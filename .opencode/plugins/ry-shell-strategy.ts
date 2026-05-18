import type { Plugin } from "@opencode-ai/plugin"

// The plugin tsconfig keeps `types: []` to avoid leaking the full Node API
// surface into Bun plugin code — declare only what we actually consume.
// Both Bun and Node runtimes expose `process.env`, so this is portable.
declare const process: { env: Record<string, string | undefined> }

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
      // Always silence interactive prompts and update notifiers — these are
      // pure UX and never break correctness. `CI=1` is broader (affects test
      // runners, package managers, watch modes, snapshot output), so allow
      // the operator to opt out via `RY_DISABLE_CI_ENV=1` for interactive
      // workflows that need TTY-aware behavior. YOLO mode keeps `CI=1` on by
      // default — see docs/decisions/009-yolo-full-auto-mode.md.
      output.env.GIT_TERMINAL_PROMPT = "0"
      output.env.NO_UPDATE_NOTIFIER = "1"
      output.env.NODE_OPTIONS = "--max-old-space-size=4096"
      if (process.env.RY_DISABLE_CI_ENV !== "1") {
        output.env.CI = "1"
      }
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
      // `-f` may be combined with other short flags into a cluster:
      // `git push -fv` (force + verbose), `-fq`, `-fn`, `-fvv`, `-vf`.
      // The narrow `(?:^|\s)-f(?:\s|$)/` only matched the standalone form.
      // Allow `f` anywhere inside an alpha-only flag cluster. Reviewer
      // wave 2026-05-18 security F-2 closure.
      const shortForce = /(?:^|\s)-[A-Za-z]*f[A-Za-z]*(?:\s|$)/
      const branchAlt = /\b(main|master|release|production)\b/i

      const isPush = /\bgit\s+push\b/i.test(command)

      if (isPush && !noVerify.test(command)) {
        await toast("warning", "git push: run quality gates and /ry-sync first")
        await log(
          "info",
          "git push detected — recommend running tests/type checks, Serena memory sync, and conventional commit verification before push",
        )
      }

      // Layer 1 (force-push without lease). Order matters: log BEFORE
      // throw so the audit trail records the block reason even when the
      // toast notification fails silently.
      if (isPush && (longForce.test(command) || shortForce.test(command)) && !lease.test(command)) {
        const msg = "Blocked git push --force / -f without --force-with-lease (data-loss risk)."
        await log("error", `${msg} cmd=${command.slice(0, 200)}`)
        await toast("error", msg)
        throw new Error(`[rldyour] ${msg} Use --force-with-lease for safer force pushes.`)
      }

      // Layer 2 (catastrophic rm -rf). Unconditional throw mirrors the
      // deny-only policy in ry-permission-policy.ts so the same pattern
      // is blocked regardless of whether bash permission is statically
      // "allow" (Build agent) or "ask" (plan + reviewer subagents).
      // node_modules cleanup is the documented allowlist exception.
      if (/\brm\s+(-rf?|-fr|--recursive)\b/i.test(command)) {
        const dangerous =
          /\brm\s+(-rf?|-fr|--recursive)\s+\/\s*$/i.test(command) ||
          /\brm\s+(-rf?|-fr|--recursive)\s+\$HOME\b/i.test(command) ||
          /\brm\s+(-rf?|-fr|--recursive)\s+~\/?\s*$/i.test(command) ||
          /\brm\s+(-rf?|-fr|--recursive)\s+\.\s*$/i.test(command) ||
          // Parent-dir traversal: `rm -rf ..` from any project subdirectory
          // erases the entire project tree. Reviewer wave 2026-05-18 security
          // F-1 closed this symmetric gap (both rm guards missed `..`).
          /\brm\s+(-rf?|-fr|--recursive)\s+\.\.\/?\s*$/i.test(command)
        const isNodeModulesCleanup =
          /\brm\s+(-rf?|-fr|--recursive)\s+\S*\/?node_modules\/?\s*$/i.test(command)
        if (dangerous && !isNodeModulesCleanup) {
          const msg = "Blocked catastrophic rm -rf target (root/home/cwd)."
          await log("error", `${msg} cmd=${command.slice(0, 200)}`)
          await toast("error", msg)
          throw new Error(`[rldyour] ${msg} Refusing to recursively delete a protected target.`)
        }
        // Non-catastrophic destructive rm: still surface a warning so
        // the operator notices, but do not block; cleanup of project
        // dirs, build outputs, and node_modules paths is legitimate.
        // Bare build-output targets like `rm -rf build` also deserve
        // operator attention even though they do not contain a slash.
        if (!isNodeModulesCleanup) {
          await toast("warning", "Destructive rm command detected — verify target before proceeding.")
          await log("warn", `destructive rm command: ${command.slice(0, 200)}`)
        }
      }

      // Layer 3 (git push --no-verify). Audit Phase 1 widened the block:
      // previously this only fired when the explicit branch token matched
      // main/master/release/production, which the bypass
      // `git push --no-verify origin HEAD` evaded when the *current* branch
      // was a product branch (no token on the command line). Now we block
      // every `--no-verify` push by default. Operators with a legitimate
      // pre-push-hook-failure case can opt out by setting
      // `RY_ALLOW_NO_VERIFY=1` in their shell before invoking the command;
      // the override is intentionally explicit so a single command-line
      // invocation cannot bypass it. branchAlt is still computed because
      // the audit log distinguishes "product branch attempt" from "feature
      // branch attempt" — same block, different signal severity.
      if (isPush && noVerify.test(command)) {
        if (process.env.RY_ALLOW_NO_VERIFY === "1") {
          await log(
            "warn",
            `RY_ALLOW_NO_VERIFY=1 override active; allowing git push --no-verify. cmd=${command.slice(0, 200)}`,
          )
        } else {
          const productBranch = branchAlt.test(command)
          const msg = productBranch
            ? "Blocked git push --no-verify (pre-push hook bypass on a product branch)."
            : "Blocked git push --no-verify (pre-push hook bypass)."
          await log("error", `${msg} cmd=${command.slice(0, 200)}`)
          await toast("error", msg)
          throw new Error(
            `[rldyour] ${msg} Resolve the hook failure, or set RY_ALLOW_NO_VERIFY=1 to opt out of this guard for a single shell session.`,
          )
        }
      }
    },
  }
}
