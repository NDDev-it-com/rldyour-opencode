import type { Plugin } from "@opencode-ai/plugin"

declare const Bun: {
  file: (path: string) => {
    exists: () => Promise<boolean>
    text: () => Promise<string>
  }
  write: (path: string, content: string) => Promise<number>
}

const MAX_LOG_BYTES = 256 * 1024 // 256 KiB; rotates with reset when exceeded.

function sanitizeArgs(raw: string): string {
  // Args may contain user-pasted text. Strip anything that looks like a
  // credential pattern before logging; truncate to keep audit lines small.
  const stripped = raw
    .replace(/sk-[A-Za-z0-9_\-]{8,}/g, "<redacted-api-key>")        // OpenAI / Anthropic
    .replace(/ghp_[A-Za-z0-9]{8,}/g, "<redacted-pat>")              // GitHub classic PAT
    .replace(/ghs_[A-Za-z0-9]{8,}/g, "<redacted-gh-server-token>")  // GitHub server-to-server
    .replace(/gho_[A-Za-z0-9]{8,}/g, "<redacted-gh-oauth>")         // GitHub OAuth user token
    .replace(/glpat-[A-Za-z0-9_\-]{8,}/g, "<redacted-gitlab-pat>")  // GitLab PAT
    .replace(/AKIA[0-9A-Z]{16}/g, "<redacted-aws-access-key>")      // AWS access key id
    .replace(/ASIA[0-9A-Z]{16}/g, "<redacted-aws-session-key>")     // AWS session access key id
    .replace(/xox[abprs]-[A-Za-z0-9\-]+/g, "<redacted-slack-token>") // Slack tokens
    .replace(/eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}/g, "<redacted-jwt>") // JWT
    .replace(/-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----/g, "<redacted-pem>")
    // Fallback: any opaque alphanumeric/underscore/hyphen run of 32+ chars
    // is treated as a potential credential. Threshold 32 covers AWS Secret
    // Access Key (40 chars), opaque API tokens, OAuth refresh tokens, and
    // JWT segments while still allowing short identifiers like UUIDs without
    // hyphens (32 chars hex) — those are also redacted, accepted false-positive.
    .replace(/[A-Za-z0-9_\-]{32,}/g, "<redacted-long-token>")
  return stripped.slice(0, 280)
}

export const RyCommandAudit: Plugin = async ({ directory }) => {
  // PluginInput.directory is always defined per @opencode-ai/plugin v1.14
  // type contract (string, not nullable). The previous `project.path`
  // fallback was dead code — Project type does not expose `path`.
  const projectDir = directory
  const auditPath = projectDir.endsWith("/")
    ? `${projectDir}.serena/.command_audit.log`
    : `${projectDir}/.serena/.command_audit.log`

  return {
    "command.execute.before": async (input) => {
      const ts = new Date().toISOString()
      const args = typeof input.arguments === "string" ? input.arguments : JSON.stringify(input.arguments ?? "")
      const line = `${ts} session=${input.sessionID.slice(0, 12)} cmd=/${input.command} args=${sanitizeArgs(args)}\n`

      try {
        const f = Bun.file(auditPath)
        const existing = (await f.exists()) ? await f.text() : ""
        const next = (existing.length + line.length > MAX_LOG_BYTES)
          ? `# rotated at ${ts}\n${line}`
          : existing + line
        await Bun.write(auditPath, next)
      } catch (err) {
        console.warn(
          `[rldyour] ry-command-audit: append failed (${err instanceof Error ? err.message : String(err)})`,
        )
      }
    },
  }
}
