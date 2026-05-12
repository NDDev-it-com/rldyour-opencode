import type { Plugin } from "@opencode-ai/plugin"

export const RyFlowHooks: Plugin = async ({ project }) => {
  const projectName = project?.name ?? "unknown"

  return {
    "tool.execute.after": async (input, output) => {
      if (input.tool === "bash") {
        const command: string = output.args?.command ?? ""
        const result: string = output.result?.toString() ?? ""

        if (/\bgit\s+commit\b/i.test(command)) {
          const hasConventionalCommit = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?:\s.{10,}/m.test(result)
          if (!hasConventionalCommit) {
            console.log("[rldyour-flow] Commit advice: use Conventional Commits format (feat/fix/docs/style/refactor/perf/test/build/ci/chore/revert):")
            console.log("[rldyour-flow]   feat(scope): add new feature")
            console.log("[rldyour-flow]   fix(scope): resolve bug in module")
          }
        }

        if (/\bgit\s+(commit|merge|cherry-pick|rebase)\b/i.test(command) && !/\b--amend\b/.test(command)) {
          const headBefore = output.args?._headBefore
          if (output.result && typeof output.result === "string" && output.result.includes("changed")) {
            console.log("[rldyour-flow] Serena memories may need sync after this commit. Consider running /ry-sync.")
          }
        }
      }
    },
  }
}