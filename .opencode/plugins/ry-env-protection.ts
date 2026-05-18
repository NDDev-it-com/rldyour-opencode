import type { Plugin } from "@opencode-ai/plugin"

// IMPORTANT — scope statement: this plugin is a best-effort interactive
// guardrail, NOT a security guarantee or sandbox-grade DLP. Determined
// adversaries with shell access can bypass any in-process matcher (heredocs,
// arithmetic obfuscation, child-process redirection, full-text shell
// quoting). True protection relies on: keeping .env out of the repo, GitHub
// secret-scanning + gitleaks CI gate, least-privilege tokens, and
// granular permission rules. This plugin exists to catch obvious
// LLM-generated mistakes (cat .env into chat output, leak in a one-liner
// script) before they reach the model context, not to defeat targeted
// exfiltration. Documented in docs/security/mcp-trust-boundaries.md.

const BLOCKED_PATTERNS = [
  /\.env$/i,
  /\.env\./i,
  /credentials/i,
  // Path-component bounded matchers for the canonical sensitive directories:
  // `(^|/)\.foo/` matches `.foo/` at the start of a relative path AND `/.foo/`
  // anywhere in an absolute path. The previous `/\.ssh\//i` form silently
  // missed relative paths like `.ssh/config` or `~/.ssh/id_rsa` (no leading
  // slash). Same fix for `.gnupg` and `.aws`.
  /(^|\/)\.ssh\//i,
  /(^|\/)\.gnupg\//i,
  /(^|\/)\.aws\//i,
  // Path-bounded "secret(s)?" — matches secret / secrets / .secret(s) as
  // directory or filename component. Closes reviewer 0.11.0 finding
  // "secret-scan.yml / secret_data.py false-positives": the bare
  // /secret/i pattern previously matched any substring, blocking
  // legitimate reads of the workflow file shipped in this same release.
  /(^|\/)\.?secrets?(\.|$|\/)/i,
  /private[_-]?key/i,
  /service[_-]?account/i,
  /\.pem$/i,
  /\.p12$/i,
  /\.pfx$/i,
  /\.key$/i,
]

const ALLOWED_ENV_EXTENSIONS = [".env.example", ".env.template", ".env.sample"]

function isSensitivePath(filePath: string): boolean {
  const normalized = filePath.replace(/\\/g, "/")
  for (const ext of ALLOWED_ENV_EXTENSIONS) {
    if (normalized.endsWith(ext)) return false
  }
  return BLOCKED_PATTERNS.some((pattern) => pattern.test(normalized))
}

// Surfaces the block rationale through both client.app.log (server log file)
// and client.tui.showToast (user-visible banner) BEFORE throwing. Without
// the toast the user only sees an opaque "tool failed" with no explanation.
// Notify is best-effort: if either client call throws, we still raise the
// block — preventing a UX failure from turning into a security failure.
//
// Order matters: log BEFORE toast so the audit trail records the block
// reason even when the toast UI is unavailable or itself throws. Mirrors
// the log-first invariant in ry-shell-strategy.ts and ry-permission-
// policy.ts; reviewer wave 2026-05-18 consistency F-1 closure.
export const RyEnvProtection: Plugin = async ({ client }) => {
  async function notifyBlock(path: string, kind: "read" | "bash"): Promise<void> {
    const message =
      kind === "read"
        ? `Blocked read of sensitive file: ${path}`
        : `Blocked bash command that reads sensitive files: ${path}`
    try {
      await client.app.log({ body: { service: "ry-env-protection", level: "warn", message } })
    } catch {
      // server log unavailable; carry on
    }
    try {
      await client.tui.showToast({ body: { variant: "error", message } })
    } catch {
      // tui unavailable; carry on
    }
  }

  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read") {
        const filePath: string = output.args?.filePath ?? ""
        if (isSensitivePath(filePath)) {
          await notifyBlock(filePath, "read")
          throw new Error(
            `[rldyour] Blocked read of sensitive file: ${filePath}. Use environment variables or secret managers instead. If you need a template, use .env.example / .env.template / .env.sample.`,
          )
        }
      }

      if (input.tool === "bash") {
        const command: string = output.args?.command ?? ""

        // Four independent attack vectors. The original pattern only
        // caught (1). All four must be covered or the guard is
        // bypassable with one extra utility. Audit Phase 1 added (4).
        //
        // (1) Read/dump/edit tools targeting a sensitive path token.
        //     Expanded from cat/head/tail/less/more/type to also cover
        //     grep, sed, awk, strings, xxd, od, hexdump, cut (text +
        //     binary dumping), and bat/view/nano/vim/vi/emacs (pagers
        //     and editors that print file contents to stdout/stderr).
        // (2) One-liner script execs with -c / -e flags. Allows
        //     `python3 -c 'print(open(".env").read())'` style bypass.
        // (3) Shell redirect from a sensitive file
        //     (`grep token < secrets.env`). The redirect operator
        //     itself encodes the read intent regardless of the program.
        // (4) Data-movement utilities that copy/archive/encode the
        //     sensitive file into a non-sensitive destination
        //     (cp/mv/tar/zip/base64/find -exec). They do not read the
        //     file to stdout themselves, but they pull the bytes out of
        //     the protected location and stage them somewhere readable.
        //     Documented in audit Phase 1.
        const readTokenRe =
          /\b(cat|head|tail|less|more|type|bat|view|nano|vim|vi|emacs|grep|sed|awk|strings|xxd|od|hexdump|cut)\b/i
        const scriptExecRe = /(?:python3?|node|ruby|perl|bash|sh|fish|zsh)\s+-[ce]\b/i
        const shellRedirectRe = /<\s*[^\s|&;<>]*\.(env|pem|key|p12|pfx)\b/i
        // Security review F-1 widened the data-movement matcher. `dd`,
        // `socat`, `tee`, `curl`, `wget` all move bytes from a sensitive
        // path to a non-sensitive destination without producing direct
        // stdout, so they evade the read-token detector while still
        // performing exfiltration. They are now first-class blockers.
        const dataMoveRe =
          /\b(cp|mv|tar|zip|gzip|7z|rsync|scp|base64|openssl|find|dd|socat|tee|curl|wget)\b/i
        // `dd` and related tools use `key=value` argv syntax (`dd if=.env
        // of=/tmp/out`). Our default split on `[\s|&;<>(){}"']+` keeps
        // `if=.env` as a single token; the path-bounded `(^|/)\.foo/`
        // regex inside isSensitivePath then misses it because there is no
        // `^` or `/` before the dotfile. Add an extra splitter that breaks
        // on `=` and `:` so the value half of every `key=path` /
        // `key:path` argv pair gets its own sensitivity check.
        // Security review F-2.
        const ddArgPathRe = /\b(if|of|file|source|src|in|out)=\S*\.(env|pem|key|p12|pfx)\b/i

        // Keep backslash inside tokens: shell escapes such as `.ssh\\config`
        // still carry path information that isSensitivePath() must inspect.
        const primaryTokens = command.split(/[\s|&;<>(){}"']+/).filter(Boolean)
        const ddSplitTokens = primaryTokens.flatMap((t) => t.split(/[=:]/g).filter(Boolean))
        const tokens = [...primaryTokens, ...ddSplitTokens]
        const sensitiveToken = tokens.find((t) => isSensitivePath(t))
        const isRead = readTokenRe.test(command) || scriptExecRe.test(command)
        const isDataMove = dataMoveRe.test(command)

        if (
          ((isRead || isDataMove) && sensitiveToken) ||
          shellRedirectRe.test(command) ||
          ddArgPathRe.test(command)
        ) {
          await notifyBlock(command.slice(0, 200), "bash")
          throw new Error(
            "[rldyour] Blocked bash command that reads sensitive files. Use environment variables or secret managers instead.",
          )
        }
      }
    },
  }
}
