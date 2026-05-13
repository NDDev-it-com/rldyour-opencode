import type { Plugin } from "@opencode-ai/plugin"

const BLOCKED_PATTERNS = [
  /\.env$/i,
  /\.env\./i,
  /credentials/i,
  /\/\.ssh\//i,
  /\/\.gnupg\//i,
  /\/\.aws\//i,
  /secret/i,
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
        if (/\b(cat|head|tail|less|more|type)\b.*\.(env|pem|key|p12|pfx)\b/i.test(command)) {
          await notifyBlock(command.slice(0, 200), "bash")
          throw new Error(
            "[rldyour] Blocked bash command that reads sensitive files. Use environment variables or secret managers instead.",
          )
        }
      }
    },
  }
}
