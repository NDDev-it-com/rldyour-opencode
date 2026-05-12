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

function isSensitivePath(filePath: string): boolean {
  return BLOCKED_PATTERNS.some((pattern) => pattern.test(filePath))
}

export const RyEnvProtection: Plugin = async () => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read") {
        const filePath = output.args?.filePath ?? ""
        if (isSensitivePath(filePath)) {
          throw new Error(
            `[rldyour] Blocked read of sensitive file: ${filePath}. Use environment variables or secret managers instead.`
          )
        }
      }

      if (input.tool === "bash") {
        const command: string = output.args?.command ?? ""
        if (/\bcat\b.*\.(env|pem|key|p12|pfx)\b/i.test(command)) {
          throw new Error(
            `[rldyour] Blocked bash command that reads sensitive files. Use environment variables instead.`
          )
        }
      }
    },
  }
}