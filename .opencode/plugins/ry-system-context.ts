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

// TTL cache for branch / HEAD probes (audit P1-6 closure +
// integration-review F-3 hardening).
//
// The previous implementation cached branch / HEAD ONCE at plugin
// factory init. That worked while every checkout spawned a new OpenCode
// session, but `/ry-start` and any in-session `git checkout|switch|rebase|
// worktree add` would leave the cache stale for the remainder of the
// session — the LLM kept seeing the original branch name long after it
// had moved.
//
// 3 s TTL is short enough that any cross-turn drift is invisible in
// practice (a chat turn usually takes >> 3 s), yet long enough to dampen
// the hot path: `experimental.chat.system.transform` fires per completion
// turn and would otherwise spawn three `git` subprocesses every time.
// `git status --porcelain` is still spawned per call because dirty count
// is the most volatile of the three signals.
//
// The cache is keyed by `directory` so an OpenCode session that spans
// multiple worktrees / project roots (rare today but possible with
// experimental workspace mode) never serves a `branch=` stamp from the
// wrong tree. Single-directory invocations still hit the same entry.
const BRANCH_HEAD_CACHE_TTL_MS = 3_000

interface BranchHeadCache {
  ts: number
  branch: string
  headShort: string
}

const cacheByDirectory = new Map<string, BranchHeadCache>()

async function getBranchAndHead(directory: string): Promise<{ branch: string; headShort: string }> {
  const now = Date.now()
  const entry = cacheByDirectory.get(directory)
  if (entry && now - entry.ts < BRANCH_HEAD_CACHE_TTL_MS) {
    return { branch: entry.branch, headShort: entry.headShort }
  }
  const [branch, headShort] = await Promise.all([
    readGitOutput(directory, ["rev-parse", "--abbrev-ref", "HEAD"]),
    readGitOutput(directory, ["rev-parse", "--short=7", "HEAD"]),
  ])
  const next: BranchHeadCache = {
    ts: now,
    branch: branch || "unknown",
    headShort: headShort || "unknown",
  }
  cacheByDirectory.set(directory, next)
  return { branch: next.branch, headShort: next.headShort }
}

export const RySystemContext: Plugin = async ({ client, directory }) => {
  async function log(message: string): Promise<void> {
    try {
      await client.app.log({ body: { service: "ry-system-context", level: "info", message } })
    } catch {
      // server log unavailable; carry on
    }
  }

  return {
    "experimental.chat.system.transform": async (_input, output) => {
      const today = new Date().toISOString().slice(0, 10)
      const { branch, headShort } = await getBranchAndHead(directory)
      const status = await readGitOutput(directory, ["status", "--porcelain"])
      const dirty = status.length > 0 ? `dirty (${status.split("\n").length} files)` : "clean"

      const line = `[rldyour runtime] date=${today} branch=${branch} head=${headShort} worktree=${dirty}`
      output.system.push(line)

      // Log once per session start ground truth so the audit trail records
      // what context the LLM saw. Quiet for subsequent turns.
      if (Math.random() < 0.05) await log(line)
    },
  }
}
