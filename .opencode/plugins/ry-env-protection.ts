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

export const RyEnvProtection: Plugin = async () => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read") {
        const filePath: string = output.args?.filePath ?? ""
        if (isSensitivePath(filePath)) {
          throw new Error(
            `[rldyour] Blocked read of sensitive file: ${filePath}. Use environment variables or secret managers instead. If you need template files, use .env.example.`
          )
        }
      }

      if (input.tool === "bash") {
        const command: string = output.args?.command ?? ""
        if (/\b(cat|head|tail|less|more|type)\b.*\.(env|pem|key|p12|pfx)\b/i.test(command)) {
          throw new Error(
            `[rldyour] Blocked bash command that reads sensitive files. Use environment variables or secret managers instead.`
          )
        }
      }
    },
  }
}