import type { Plugin } from "@opencode-ai/plugin"

// Hints appended to tool descriptions seen by the LLM. Each hint is a
// one-sentence routing nudge sourced from AGENTS.md § Tool Priority and
// the domain-boundary matrix. Keep hints stable and short — they enter
// every prompt that includes the tool definition.
//
// Tool ID format: OpenCode v1.14.48 constructs MCP tool IDs at runtime
// as `sanitize(serverName) + "_" + sanitize(toolName)` where sanitize()
// replaces every char not matching [a-zA-Z0-9_-] with "_". Dashes are
// preserved. Examples: `serena_find_symbol`, `chrome-devtools_list_console_messages`,
// `context7_resolve-library-id`. The legacy `mcp__server__tool` format from
// Claude Code does NOT match here — using it would silently disable every hint.
// Source: packages/opencode/src/mcp/index.ts in sst/opencode (build line uses underscore).
const HINTS: Record<string, string> = {
  // Serena (semantic code intelligence — Serena domain only)
  "serena_find_symbol":
    "Prefer over raw `grep` when locating a known symbol; LSP-aware and faster.",
  "serena_get_symbols_overview":
    "Use BEFORE reading a whole file — cheaper file structure overview.",
  "serena_find_referencing_symbols":
    "Use to trace caller impact before any refactor.",
  "serena_search_for_pattern":
    "Use only for cross-cutting text sweeps; for symbol lookup prefer `find_symbol`.",
  "serena_read_memory":
    "Read Serena memories only when the task references prior decisions or project facts.",

  // Browser (Browser domain only)
  "playwright_browser_navigate":
    "Use for end-to-end UI validation and golden-path verification.",
  "chrome-devtools_list_console_messages":
    "Use for runtime browser diagnostics (errors, warnings), not UI validation.",
  "chrome-devtools_performance_start_trace":
    "Use only when measuring performance; avoid for routine checks.",

  // Research (Explore domain)
  "context7_resolve-library-id":
    "Call this FIRST when you have a library name but no Context7 ID — pairs with `query-docs`.",
  "context7_query-docs":
    "Preferred over `websearch` for current library API documentation. Requires the Context7 ID from `resolve-library-id`.",
  "deepwiki_ask_question":
    "Use for public-repo architecture questions when library docs are insufficient.",
  "grep_searchGitHub":
    "Use for real production usage patterns across public GitHub repos.",

  // Security (Security domain only)
  "semgrep_semgrep_scan":
    "Static analysis for defensive security review — outputs require manual validation.",

  // Planning
  "sequential-thinking_sequentialthinking":
    "Use for non-trivial architectural or design decisions before editing.",
}

export const RyToolHints: Plugin = async () => {
  return {
    "tool.definition": async (input, output) => {
      const hint = HINTS[input.toolID]
      if (hint) {
        output.description = `${output.description}\n\n[rldyour hint] ${hint}`
      }
    },
  }
}
