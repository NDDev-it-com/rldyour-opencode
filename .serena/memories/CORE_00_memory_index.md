# CORE_00 Memory Index

## Purpose

This index tracks all verified high-signal memories for rldyour-opencode. Each entry points to a memory file that contains durable facts about the project.

## Memory Registry

| ID | File | Scope | Description |
| --- | --- | --- | --- |
| CORE_00 | `CORE_00_memory_index.md` | project | Master memory index and registry |

## Project Facts

- **Repository**: rldyour-opencode
- **Type**: OpenCode configuration marketplace
- **Primary config**: `opencode.json`
- **Agents**: `.opencode/agents/*.md` (9 agent definitions)
- **Skills**: `.opencode/skills/*/SKILL.md` (30+ skill definitions)
- **Commands**: `.opencode/commands/*.md` (6 command templates)
- **References**: `references/*.md` (15 reference documents)
- **Scripts**: `scripts/*.sh` (3 diagnostic/bootstrap scripts)
- **Serena languages**: yaml, json, markdown, bash
- **Communication**: Russian (user-facing), English (repository artifacts)
- **Commit convention**: Conventional Commits v1.0.0
- **Quality priority**: Correctness > Architecture > Consistency > Speed

## Architecture

```
rldyour-opencode/
├── AGENTS.md              # Cross-tool root instructions
├── opencode.json          # Master OpenCode configuration
├── .opencode/
│   ├── agents/            # Subagent definitions (flow-*, ry-explore)
│   ├── skills/            # On-demand skill definitions
│   └── commands/          # Slash command templates (ry-*)
├── .serena/
│   ├── project.yml        # Serena project configuration
│   └── memories/          # Verified project knowledge
├── references/            # Durable reference documentation
├── scripts/               # Validation and diagnostic scripts
├── thinking/              # Sequential thinking artifacts
├── VERSION                # Current version
├── CHANGELOG.md           # Change history
├── LICENSE                # MIT license
└── README.md              # Repository documentation
```

## Last commit SHA

Initialized during project bootstrap.

## Anti-Hallucination Contract

Every factual claim in this memory and linked memories must trace to a verifiable source: current file content, git history, or explicit user input. Never speculate, paraphrase advice, or copy chat history. Remove unverifiable claims immediately.
