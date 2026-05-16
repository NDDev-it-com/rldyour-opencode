<!-- Memory Metadata
Last updated: 2026-05-17
Last commit: dd149aa chore(opencode): align plugin pin with runtime 1.15.3
Scope: AGENTS.md, .claude/CLAUDE.md, references/reviewer-protocol.md, references/project-instructions-and-adrs.md, docs/, docs/decisions/
Area: DOCS
-->

# DOCS-01-INSTRUCTIONS

## Purpose

Durable instruction and documentation contracts for the OpenCode marketplace, including root AI instructions, Claude Code parity, reviewer protocol, operator docs, and ADR supersession behavior.

## Source Of Truth

- `AGENTS.md`: root cross-tool project instructions for AI agents.
- `.claude/CLAUDE.md`: first-class Claude Code project instruction file, maintained separately from `AGENTS.md`.
- `references/reviewer-protocol.md`: review subagent contract and model-inheritance policy.
- `references/project-instructions-and-adrs.md`: instruction and ADR policy.
- `docs/release-process.md`, `docs/dependency-updates.md`, `docs/rollback-restore.md`, `docs/observability.md`: marketplace operator guides.
- `docs/decisions/001-architecture-and-plan.md` through `004-phased-implementation.md`: ADR archive.

## Entry Points

- `scripts/validate_instruction_docs.py`: validates required instruction docs and anchor headings.
- `python3 scripts/validate_instruction_docs.py --require-agent-docs`: stricter instruction-docs validation gate.
- `references/reviewer-protocol.md`: reviewer agents and orchestrators use this protocol for track behavior.

## Current Behavior

- `AGENTS.md` now contains the project-specific OpenCode instructions and explicitly lists source-of-truth files, domain boundaries, OpenCode conventions, built-in tools, plugin routing, LSP policy, validation commands, git/fullrepo sync, and done criteria.
- `references/reviewer-protocol.md` states that reviewer agents have no model override and inherit `opencode.json` top-level `model` (`opencode-go/glm-5.1` at this HEAD).
- All 4 ADR files have a 2026-05-14 supersession banner: old Claude model IDs in preserved code examples are historical and current agent configs inherit from top-level `model`.
- `docs/` is operator-facing; `references/` is consumed by skills and agents as durable contracts. They are complementary, not redundant.

## Contracts And Data

- `AGENTS.md` must remain OpenCode-native and must not describe Claude Code or Codex constructs as current OpenCode behavior.
- `.claude/CLAUDE.md` remains a separate first-class file optimized for Claude Code and must not be reduced to only an `@AGENTS.md` import.
- ADR text can preserve historical examples when a top-of-file banner clarifies supersession and current behavior.
- Reviewer protocol must not hardcode a specific model when runtime policy is top-level model inheritance.

## Invariants

- Instruction docs must be refreshed from verified code/config state, not from stale memories.
- If `opencode.json` model, MCP, permissions, agents, plugins, or sync policy changes, update instruction docs and memories in the same task closure.
- Do not store secrets, tokens, local credentials, or runtime logs in docs or memories.

## Change Rules

- Use `instruction-docs-sync` for AGENTS/Claude instruction synchronization work.
- Use `project-instructions-policy` for durable instruction, ADR, and review-protocol policy changes.
- After instruction doc changes, run `scripts/validate_instruction_docs.py` and the broader config/test gates when the touched surface affects runtime behavior.

## Verification

- `python3 scripts/validate_instruction_docs.py --require-agent-docs`: verifies instruction docs exist and required headings are present.
- `bash scripts/validate_config.sh`: verifies OpenCode config and frontmatter after docs/prompt changes that affect agent/skill/command files.
- `rg -n 'model override|inherit|mcp__|opencode-go/glm' AGENTS.md references/reviewer-protocol.md docs/decisions .opencode`: verifies docs align with current model and tool naming policy.
