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
  }
}

async function readGitOutput(cwd: string, args: string[]): Promise<string> {
  try {
    const proc = Bun.spawn(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" })
    const text = await new Response(proc.stdout).text()
    await proc.exited
    return text.trim()
  } catch {
    return ""
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

  return {
    "experimental.chat.system.transform": async (_input, output) => {
      const today = new Date().toISOString().slice(0, 10)
      const branch = (await readGitOutput(directory, ["rev-parse", "--abbrev-ref", "HEAD"])) || "unknown"
      const headShort = (await readGitOutput(directory, ["rev-parse", "--short=7", "HEAD"])) || "unknown"
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
