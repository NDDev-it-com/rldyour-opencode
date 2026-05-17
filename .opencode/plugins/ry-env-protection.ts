import type { Plugin } from "@opencode-ai/plugin"

const BLOCKED_PATTERNS = [
  /\.env$/i,
  /\.env\./i,
  /credentials/i,
  /\/\.ssh\//i,
  /\/\.gnupg\//i,
  /\/\.aws\//i,
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
export const RyEnvProtection: Plugin = async ({ client }) => {
  async function notifyBlock(path: string, kind: "read" | "bash"): Promise<void> {
    const message =
      kind === "read"
        ? `Blocked read of sensitive file: ${path}`
        : `Blocked bash command that reads sensitive files: ${path}`
    try {
      await client.tui.showToast({ body: { variant: "error", message } })
    } catch {
      // tui unavailable; carry on
    }
    try {
      await client.app.log({ body: { service: "ry-env-protection", level: "warn", message } })
    } catch {
      // server log unavailable; carry on
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

        // Three independent attack vectors. The original pattern only
        // caught (1). All three must be covered or the guard is
        // bypassable with one extra utility.
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
        const readTokenRe =
          /\b(cat|head|tail|less|more|type|bat|view|nano|vim|vi|emacs|grep|sed|awk|strings|xxd|od|hexdump|cut)\b/i
        const scriptExecRe = /(?:python3?|node|ruby|perl|bash|sh|fish|zsh)\s+-[ce]\b/i
        const shellRedirectRe = /<\s*[^\s|&;<>]*\.(env|pem|key|p12|pfx)\b/i

        const tokens = command.split(/[\s|&;<>(){}\\"']+/).filter(Boolean)
        const sensitiveToken = tokens.find((t) => isSensitivePath(t))
        const isRead = readTokenRe.test(command) || scriptExecRe.test(command)

        if ((isRead && sensitiveToken) || shellRedirectRe.test(command)) {
          await notifyBlock(command.slice(0, 200), "bash")
          throw new Error(
            "[rldyour] Blocked bash command that reads sensitive files. Use environment variables or secret managers instead.",
          )
        }
      }
    },
  }
}
