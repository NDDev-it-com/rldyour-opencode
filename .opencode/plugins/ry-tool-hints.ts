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
    "Используй вместо raw `grep` для поиска известного symbol; EN: LSP-aware and faster.",
  "serena_get_symbols_overview":
    "Используй перед чтением всего файла; EN: cheaper file-structure overview.",
  "serena_find_referencing_symbols":
    "Используй для трассировки caller impact перед refactor; EN: references before edits.",
  "serena_search_for_pattern":
    "Используй только для сквозных text sweeps; EN: prefer `find_symbol` for symbol lookup.",
  "serena_read_memory":
    "Читай Serena memories для прошлых решений или durable project facts; EN: not for chat logs.",

  // Browser DevTools diagnosis (Browser domain only). Playwright CLI is routed by skills, not MCP tool hints.
  "chrome-devtools_list_console_messages":
    "Используй для runtime browser diagnostics ошибок/предупреждений; EN: not visual UI validation.",
  "chrome-devtools_performance_start_trace":
    "Используй только для performance measurement; EN: avoid routine trace overhead.",

  // Research (Explore domain)
  "context7_resolve-library-id":
    "Сначала вызывай для library name без Context7 ID; EN: pair with `query-docs`.",
  "context7_query-docs":
    "Предпочитай для текущей library/API документации; EN: requires Context7 ID before websearch.",
  "deepwiki_ask_question":
    "Используй для architecture questions по public repos; EN: when docs are insufficient.",
  "grep_searchGitHub":
    "Используй для production patterns в public GitHub repos; EN: real-world usage evidence.",

  // Planning
  "sequential-thinking_sequentialthinking":
    "Используй для нетривиальных architecture/design решений перед edits; EN: plan first.",
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
