import type { Plugin } from "@opencode-ai/plugin"

// We deliberately stay on Bun's native APIs instead of importing `node:fs`
// or `node:path` to keep the plugin tsconfig `types: []` baseline working
// without pulling in `@types/node`. Bun.write performs an atomic
// write-then-rename internally, so we get crash safety without a manual
// temp+rename dance. Parent directories must exist before the write — we
// ensure that via the Bun shell helper below.
declare const Bun: {
  file: (path: string) => {
    exists: () => Promise<boolean>
    text: () => Promise<string>
  }
  write: (path: string, content: string) => Promise<number>
  spawn: (
    cmd: string[],
    opts?: { cwd?: string; stdout?: "pipe" | "inherit"; stderr?: "pipe" | "inherit" },
  ) => { exited: Promise<number> }
}

function parentDir(path: string): string {
  const idx = path.lastIndexOf("/")
  return idx <= 0 ? "." : path.slice(0, idx)
}

async function ensureDir(path: string): Promise<void> {
  // `mkdir -p` is idempotent and cheap. Spawning the system mkdir avoids the
  // `node:fs/promises` import — see top-of-file note about tsconfig types.
  const proc = Bun.spawn(["mkdir", "-p", path], { stdout: "pipe", stderr: "pipe" })
  await proc.exited
}

const MAX_LOG_BYTES = 256 * 1024 // 256 KiB; rotates with reset when exceeded.

// Concurrency note (Quality review F-4): the read-modify-write sequence
// below is not atomic. OpenCode runs plugin hooks on a single Bun event
// loop, so within one process two `command.execute.before` callbacks are
// serialised by the runtime and cannot interleave. The only path that
// would lose an audit line is two *separate* OpenCode processes writing
// to the same project tree concurrently — an unsupported configuration.
// Documenting the invariant rather than adding a lock (cheaper, sufficient).
//
// Order note (Quality review F-3): sanitize() runs on the full raw args
// string BEFORE the 280-char slice — this guarantees a credential at any
// offset is redacted before the line is truncated. If we sliced first,
// a credential appearing past byte 280 would be silently dropped, which
// is fine, but a credential straddling the cut would leak its prefix.
// Sanitize-first preserves the invariant "no credential ever reaches the
// log, regardless of position".

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

export const RyCommandAudit: Plugin = async ({ client, directory }) => {
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
        // Audit Phase 1: make the audit append resilient to the two failure
        // modes the original code couldn't handle.
        //
        // (1) Missing `.serena/` directory. On a freshly cloned repo where
        //     the agent-only files have not been restored from `fullrepo`
        //     yet, the parent directory does not exist and Bun.write would
        //     silently fail. `ensureDir` runs `mkdir -p` which is
        //     idempotent and cheap.
        // (2) Multi-instance write race. The read-modify-write sequence
        //     in the original code could lose audit lines when two
        //     OpenCode instances target the same project tree (a
        //     configuration that became more relevant once upstream
        //     v1.15.4 fixed project-scoped bus events). Bun.write performs
        //     an atomic write-then-rename internally, so the final replace
        //     is crash-safe. The remaining read-modify-write race window
        //     (between `f.text()` and `Bun.write`) is documented and
        //     accepted — within a single OpenCode instance, plugin hooks
        //     are serialised by the Bun event loop, so the race only
        //     applies to genuinely concurrent OpenCode processes targeting
        //     the same project. That scenario sacrifices at most one audit
        //     line per overlap, which is acceptable for a best-effort
        //     audit log.
        await ensureDir(parentDir(auditPath))
        const f = Bun.file(auditPath)
        const existing = (await f.exists()) ? await f.text() : ""
        const next = (existing.length + line.length > MAX_LOG_BYTES)
          ? `# rotated at ${ts}\n${line}`
          : existing + line
        await Bun.write(auditPath, next)
      } catch (err) {
        const message = `ry-command-audit append failed: ${err instanceof Error ? err.message : String(err)}`
        try {
          await client.app.log({ body: { service: "ry-command-audit", level: "warn", message } })
        } catch {
          // server log unavailable; carry on — the audit miss is best-effort
        }
      }
    },
  }
}
