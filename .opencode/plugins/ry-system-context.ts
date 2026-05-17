import type { Plugin } from "@opencode-ai/plugin"

// Inject dynamic context (today's date, current git branch, recent git
// activity) into the system prompt on every chat completion. AGENTS.md
// is static and cannot communicate "now" facts; the LLM otherwise has
// no reliable way to ground answers in current branch / date.
//
// Hook: experimental.chat.system.transform — runs before each completion
// and lets us push extra lines into the system prompt without touching
// AGENTS.md or the user prompt. Source: SDK dist/index.d.ts:267-273.
//
// All filesystem / git probes have short timeouts and silent fallbacks so
// transient failures cannot block the model call.

declare const Bun: {
  spawn: (cmd: string[], opts?: { cwd?: string; stdout?: "pipe"; stderr?: "pipe" }) => {
    exited: Promise<number>
    stdout: ReadableStream
    stderr: ReadableStream
    kill: (signal?: number | string) => void
  }
}

// `experimental.chat.system.transform` runs before every model call, so the
// git status probe MUST be ultra-fast and fail-open. Without an explicit
// timeout+kill guard, a stuck `git status` (lockfile contention, slow FS,
// network FS) could stall every chat turn. 800ms is a tight cap that still
// allows a healthy local clone to respond. maxBytes caps the largest realistic
// `git status --porcelain` output (a 16 KiB string corresponds to ~250 files)
// — anything bigger gets truncated, the worktree dirty count uses the line
// count of the truncated text which is acceptable for the system-prompt
// stamp. Pattern is duplicated in ry-tools.ts on purpose; the limits differ.
async function readGitOutput(
  cwd: string,
  args: string[],
  timeoutMs = 800,
  maxBytes = 16_384,
): Promise<string> {
  let proc: ReturnType<typeof Bun.spawn> | undefined
  let killed = false
  const timer = setTimeout(() => {
    killed = true
    try {
      proc?.kill()
    } catch {
      // process may have already exited
    }
  }, timeoutMs)
  try {
    proc = Bun.spawn(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" })
    const text = await new Response(proc.stdout).text()
    await proc.exited
    if (killed) return ""
    return (text.length > maxBytes ? text.slice(0, maxBytes) : text).trim()
  } catch {
    return ""
  } finally {
    clearTimeout(timer)
  }
}

export const RySystemContext: Plugin = async ({ client, directory }) => {
  async function log(message: string): Promise<void> {
    try {
      await client.app.log({ body: { service: "ry-system-context", level: "info", message } })
    } catch {
      // server log unavailable; carry on
    }
  }

  // Performance: `branch` and `headShort` are session-stable in any normal
  // workflow (a checkout creates a new OpenCode session via /ry-init).
  // Cache them once at factory init so the hot path (`experimental.chat
  // .system.transform` fires per chat completion turn) only spawns the
  // turn-volatile `git status --porcelain` probe — saves 2 subprocess
  // spawns per turn × N turns per session.
  const cachedBranch = (await readGitOutput(directory, ["rev-parse", "--abbrev-ref", "HEAD"])) || "unknown"
  const cachedHeadShort = (await readGitOutput(directory, ["rev-parse", "--short=7", "HEAD"])) || "unknown"

  return {
    "experimental.chat.system.transform": async (_input, output) => {
      const today = new Date().toISOString().slice(0, 10)
      const status = await readGitOutput(directory, ["status", "--porcelain"])
      const dirty = status.length > 0 ? `dirty (${status.split("\n").length} files)` : "clean"

      const line = `[rldyour runtime] date=${today} branch=${cachedBranch} head=${cachedHeadShort} worktree=${dirty}`
      output.system.push(line)

      // Log once per session start ground truth so the audit trail records
      // what context the LLM saw. Quiet for subsequent turns.
      if (Math.random() < 0.05) await log(line)
    },
  }
}
