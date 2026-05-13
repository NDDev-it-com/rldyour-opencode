---
description: "Scoped read-only инициализация контекста проекта: Serena discovery + fullrepo bootstrap + verified context pack. Initialize scoped project context (read-only)."
agent: build
---

Initialize the current project scope. Run the full init workflow:

1. Git sync audit: dirty state, current branch, upstream ahead/behind, worktrees, local/remote branches.
2. Bootstrap agent-only context before treating instruction docs or Serena files as missing.
3. Serena readiness: check onboarding, list memories, read relevant memories.
4. Scope detection: classify as project, sphere, module, or feature. If ambiguous, ask the user in Russian with 2-3 concrete options.
5. Semantic map: use Serena-first for supported code (get_symbols_overview, targeted find_symbol, find_referencing_symbols, search_for_pattern). Fall back to rg/file reads for manifests, Markdown, config, shell scripts, or unsupported languages.
6. Data and contract map: database tables/fields, schemas, migrations, API contracts, generated artifacts, configuration keys, environment variables, and integration boundaries that affect the scope.
7. Pattern map: established project patterns for naming, layering, validation, errors, tests, state management, and dependency usage.
8. External enrichment only for unclear architecture, framework behavior, or current best practices.
9. Synthesis in Russian, with exact source-of-truth paths, symbols, contracts, checks, known gaps, and memory candidates (not written).

Do not write Serena memories by default. Report candidate memory updates but run serena-memory-sync only when explicitly requested.

Reference: references/init-context-pack.md, references/flow-lifecycle.md
