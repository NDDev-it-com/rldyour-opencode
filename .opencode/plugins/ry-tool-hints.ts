import type { Plugin } from "@opencode-ai/plugin"

// Hints appended to tool descriptions seen by the LLM. Each hint is a
// one-sentence routing nudge sourced from AGENTS.md § Tool Priority and
// the domain-boundary matrix. Keep hints stable and short — they enter
// every prompt that includes the tool definition.
const HINTS: Record<string, string> = {
  // Serena (semantic code intelligence — Serena domain only)
  "mcp__serena__find_symbol":
    "Prefer over raw `grep` when locating a known symbol; LSP-aware and faster.",
  "mcp__serena__get_symbols_overview":
    "Use BEFORE reading a whole file — cheaper file structure overview.",
  "mcp__serena__find_referencing_symbols":
    "Use to trace caller impact before any refactor.",
  "mcp__serena__search_for_pattern":
    "Use only for cross-cutting text sweeps; for symbol lookup prefer `find_symbol`.",
  "mcp__serena__read_memory":
    "Read Serena memories only when the task references prior decisions or project facts.",

  // Browser (Browser domain only)
  "mcp__playwright__browser_navigate":
    "Use for end-to-end UI validation and golden-path verification.",
  "mcp__chrome-devtools__list_console_messages":
    "Use for runtime browser diagnostics (errors, warnings), not UI validation.",
  "mcp__chrome-devtools__performance_start_trace":
    "Use only when measuring performance; avoid for routine checks.",

  // Research (Explore domain)
  "mcp__context7__get-library-docs":
    "Preferred over `websearch` for current library API documentation.",
  "mcp__deepwiki__ask_question":
    "Use for public-repo architecture questions when library docs are insufficient.",
  "mcp__grep__searchGitHub":
    "Use for real production usage patterns across public GitHub repos.",

  // Security (Security domain only)
  "mcp__semgrep__semgrep_scan":
    "Static analysis for defensive security review — outputs require manual validation.",

  // Planning
  "mcp__sequential-thinking__sequentialthinking":
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
