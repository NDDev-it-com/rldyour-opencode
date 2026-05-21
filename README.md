# rldyour-opencode

Personal OpenCode configuration marketplace authored by Danil Silantyev (github:rldyourmnd), CEO NDDev. Russian-first SDLC workflow, Serena integration, MCP transport, code review, design, security, LSP, and engineering rules -- all native to the OpenCode AI coding agent format (no Claude Code or Codex residue).

Validated against OpenCode, `@opencode-ai/plugin`, and `@opencode-ai/sdk` 1.15.6 (May 2026); the OpenCode v1.14.48 → v1.15.6 plugin pin bumps preserve the runtime hook surface and tool-ID naming while picking up current plugin-loading and config-robustness fixes.

## What This Is

A self-contained OpenCode project configuration that provides:

- **33 skills** for automatic workflow routing across 10 domains (SDLC, Serena, rules, explore, browser, design, security, LSP, docs sync, config).
- **9 subagents** for specialized tasks (6 reviewer tracks, memory sync, deep research, config helper).
- **10 slash commands** for lifecycle orchestration:
  - `/ry-init`, `/ry-start`, `/ry-review`, `/ry-repair`, `/ry-newp`, `/ry-deploy`, `/ry-sync`
  - `/ry-design`, `/ry-explore`, `/ry-sec-review`, `/ry-rules-review`
- **13 MCP servers** pre-configured (Serena, Sequential Thinking, Playwright, Chrome DevTools, Context7, DeepWiki, Grep, Semgrep, shadcn, dart-flutter, Figma, GitHub, OpenAI docs).
- **10 TypeScript plugins** for session lifecycle, LLM augmentation, guardrails, and observability:
  - lifecycle: `ry-bootstrap` (session banner + compaction context + autocontinue), `ry-env-protection` (block sensitive reads with toast), `ry-shell-strategy` (shell env + git push guardrails), `ry-sync-reminder` (idle toast), `ry-flow-hooks` (commit advice + post-commit nudge)
  - LLM-side: `ry-tools` (5 custom diagnostic tools the LLM can call), `ry-command-audit` (credential-sanitized slash-command audit log), `ry-tool-hints` (routing nudges injected into MCP tool descriptions)
  - Runtime context + permission events: `ry-system-context` (date + branch + HEAD SHA + dirty state injected into every system prompt), `ry-permission-events` (observability-only `permission.asked` / `permission.replied` event audit)
- **8 custom LSP servers** on top of OpenCode's 35+ built-ins (ruff, vscode-html, vscode-css, vscode-json, docker, taplo, marksman, qmlls).
- **Owner-standard full-auto permissions** by default: primary agents allow `edit` and `bash`; reviewer subagents are read-only with git-only bash allowlists, and deterministic `tool.execute.before` guardrails still block the repository's high-impact dangerous shell patterns.

## Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/NDDev-it-com/rldyour-opencode.git
   cd rldyour-opencode
   ```

2. Copy the configuration into your project:
   ```bash
   cp opencode.json /path/to/your/project/opencode.json
   cp -r .opencode /path/to/your/project/.opencode
   cp AGENTS.md /path/to/your/project/AGENTS.md
   ```

3. Authenticate the primary OpenCode provider via TUI (recommended) or env vars:
   ```bash
   # primary provider for top-level model `opencode-go/glm-5.1` — log in interactively
   opencode auth login          # or use /providers inside the TUI

   # MCP env vars (placeholder values — replace with real credentials in your shell or .env)
   export GITHUB_PERSONAL_ACCESS_TOKEN=YOUR_PLACEHOLDER_TOKEN  # required for GitHub MCP
   export CONTEXT7_API_KEY=YOUR_PLACEHOLDER_KEY               # optional, higher Context7 rate

   # Alternative OpenCode providers (optional — only when switching the top-level model)
   # export ANTHROPIC_API_KEY=YOUR_PLACEHOLDER_KEY
   # export OPENAI_API_KEY=YOUR_PLACEHOLDER_KEY
   ```

4. Run OpenCode in your project:
   ```bash
   cd /path/to/your/project
   opencode
   ```

5. Initialize project context:
   ```
   /ry-init
   ```

## Catalog

| Layer | Where | Count |
|---|---|---|
| Master config | `opencode.json` | 1 |
| Cross-tool instructions | `AGENTS.md` | 1 |
| Claude Code project memory (agent-only) | `.claude/CLAUDE.md` | 1 |
| Subagents | `.opencode/agents/*.md` | 9 |
| Skills | `.opencode/skills/<name>/SKILL.md` | 33 |
| Slash commands | `.opencode/commands/*.md` | 11 |
| Plugins | `.opencode/plugins/*.ts` | 10 |
| Custom diagnostic tools | `.opencode/plugins/ry-tools.ts` | 5 |
| MCP servers | `opencode.json` → `mcp` | 13 |
| Custom LSP servers | `opencode.json` → `lsp` | 8 |
| Reference docs (skill/agent contracts + machine contracts) | `references/*` | 22 |
| Operator guides | `docs/*.md` | 5 (`release-process`, `dependency-updates`, `rollback-restore`, `observability`, `contract-matrix`) |
| Architecture decision archive | `docs/decisions/*.md` | 10 |
| Diagnostic scripts (bash + python) | `scripts/` | 30 (17 python files + 13 bash entry points; new in 0.13.2: `check_plugin_hooks.py`, `validate_contract.py`) |
| Pytest suites | `scripts/tests/*.py` | 26 (includes plugin hook and adapter contract validators, public-repo CI/CD automation policy, and the release-baseline changelog regression) |
| CI workflows | `.github/workflows/*.yml` | 11 (`validate`, `dependency-check`, `instruction-docs-check`, `typecheck-plugins`, `lint`, `codeql`, `secret-scan`, `dependency-review`, `release`, `sbom`, `opencode-runtime`) |

### Project structure

```
rldyour-opencode/
├── AGENTS.md                   # cross-tool root instructions
├── opencode.json               # master OpenCode config (model, MCP, LSP, agent, watcher, compaction)
├── VERSION, CHANGELOG.md
├── README.md, LICENSE, .env.example
├── pyrightconfig.json          # Python static type config for scripts/
├── .claude/CLAUDE.md           # Claude-Code-specific project memory (agent-only)
├── .opencode/
│   ├── agents/   *.md          # 9 subagents (6 reviewer, memory-sync, ry-explore, customize-opencode)
│   ├── skills/   <name>/SKILL.md  # 33 skills across 10 domains
│   ├── commands/ *.md          # 10 slash commands
│   ├── plugins/  *.ts          # 10 Bun-runtime plugins
│   └── package.json            # @opencode-ai/plugin pin
├── .serena/
│   ├── memories/  *.md         # 6 verified knowledge files (AREA-NN-SLUG.md taxonomy)
│   └── project.yml             # Serena project config
├── references/   *             # durable contracts + machine-readable adapter metadata
├── docs/
│   ├── release-process.md, dependency-updates.md, rollback-restore.md, observability.md, contract-matrix.md
│   └── decisions/  001..010.md # 10 MADR-style ADRs
├── scripts/                    # 30 bash + python diagnostic / validation / smoke scripts
│   └── tests/  *.py            # 26 pytest suites
└── .github/workflows/          # 11 least-privilege, SHA-pinned CI/release workflows
```

## Commands

| Command | Agent | Purpose |
|---|---|---|
| `/ry-init` | `build` | Scoped read-only project context with Serena-first discovery |
| `/ry-start` | `build` | Full task lifecycle: init → research → plan → implement → verify → review → sync |
| `/ry-review` | `plan` | Report-only deep review with parallel reviewer subagents |
| `/ry-repair` | `build` | Repair stale docs, memories, contracts, hooks, MCP/LSP config, CI, and AI-tool context |
| `/ry-newp` | `build` | Plan a new project (skeptical questions, research, ADRs, architecture docs) |
| `/ry-deploy` | `build` | Deploy with sync, log checks, fix-forward |
| `/ry-sync` | `build` | Synchronize memories, docs, git, and fullrepo |
| `/ry-design` | `build` | End-to-end design: Figma → tokens → FSD → shadcn/ui → browser validation |
| `/ry-explore` | `ry-explore` (subtask) | Deep multi-source research via Context7 / DeepWiki / Grep / web |
| `/ry-sec-review` | `plan` | Defensive Mythos-style security review |
| `/ry-rules-review` | `plan` | Audit implementation against rldyour rules (report-only) |

`build` remains the implementation agent, and its repository configuration uses
owner-standard full-auto permissions: `edit: "allow"` and `bash: "allow"`.
The `plan` primary agent uses the same full-auto baseline. Reviewer subagents
remain stricter (`edit: "deny"`, git-only read bash allowlists) because their
role contract is report-only review, not implementation.

## Reviewer Subagents

All reviewer tracks are `mode: subagent`, `hidden: true`, `edit: deny`, with `bash` allowlist limited to read-only git verbs. Invoke directly via `@<name>` or transitively via `/ry-start`/`/ry-review`.

| Agent | Color | Focus |
|---|---|---|
| `@flow-architecture-review` | `#3b82f6` | Boundaries, dependency direction, public API, data flow |
| `@flow-quality-review` | `success` | Correctness, edge cases, error handling, resource lifecycle |
| `@flow-consistency-review` | `#a855f7` | Naming, style, imports, project conventions |
| `@flow-integration-review` | `warning` | Cross-module contracts, schemas, configs, backward compatibility |
| `@flow-verification-review` | `#ec4899` | Tests, quality gates, browser/server evidence |
| `@flow-security-review` | `error` | OWASP Top 10, auth/authz, injection, secrets (defensive-only) |
| `@flow-memory-sync` | `#eab308` | Fact-only Serena memory synchronization |
| `@ry-explore` | `info` | Deep multi-source research (90 reasoning steps; inherits top-level `model`) |
| `@customize-opencode` | `accent` | Safely edit `opencode.json` with validation, backup, rollback |

## MCP Servers

Local servers timeout 30 s, remote 15 s. Launcher convention: `bunx` for npm, `uvx` for Python, `dart` for Dart SDK — never `npx`.

| Server | Type | Version | Purpose |
|---|---|---|---|
| serena | local (uvx) | 1.5.1 | Semantic code navigation, analysis, editing |
| sequential-thinking | local (bunx) | 2025.12.18 | Structured reasoning |
| playwright | local (bunx) | 0.0.75 | Browser automation, UI validation |
| chrome-devtools | local (bunx) | 1.0.1 | Chrome DevTools diagnostics |
| semgrep | local (uvx) | 1.163.0 | Static analysis and security |
| shadcn | local (bunx) | 4.8.0 | shadcn/ui registry access |
| dart-flutter | local (dart) | — | Dart/Flutter project support |
| context7 | remote | — | Current library documentation |
| deepwiki | remote | — | Repository documentation |
| grep | remote | — | Search across public GitHub repos |
| figma | remote | — | Figma design context |
| github | remote | toolsets: context,repos,issues,pull_requests,users | GitHub Copilot MCP (requires PAT) |
| openai-docs | remote | — | Official OpenAI/Codex documentation |

## Models

The marketplace ships with `opencode-go/glm-5.1` as the top-level default — owner's working provider. Subagents inherit this model (no per-agent override at HEAD). Switch any field to a different provider via `provider/model-id` format.

Versioning note: root `VERSION` is the marketplace/product release version.
`.opencode/package.json.version` is a private local plugin package version for
Bun dependency resolution and intentionally does not mirror root `VERSION`.

| Slot | Default in this repo | Common Anthropic alternative |
|---|---|---|
| `model` (primary) | `opencode-go/glm-5.1` | `anthropic/claude-sonnet-4-6` |
| `small_model` | `opencode-go/glm-5.1` | `anthropic/claude-haiku-4-5-20251001` |
| `default_agent` | `build` | `build` |
| Reviewer / memory-sync / explore subagents | inherit top-level `model` | inherit top-level `model` |

To switch:

```bash
opencode auth login                            # authenticate with the new provider
# edit opencode.json:  "model": "anthropic/claude-sonnet-4-6"
opencode debug config | grep -E '"model":'     # confirm runtime resolved the change
```

Run `opencode models <provider>` to list every accepted ID. All current IDs are validated by `opencode debug config` (the same runtime smoke `scripts/validate_config.sh` invokes when the CLI is on PATH).

## Validation

```bash
bash scripts/validate_config.sh                            # JSON shape + skill/agent/command frontmatter (strict YAML) + VERSION semver
uvx --from "pytest==9.0.3" --with "pyyaml==6.0.3" --with "jsonschema==4.26.0" --with "referencing==0.36.2" pytest scripts/tests/
bash scripts/check_deps_freshness.sh --check-freshness     # list pinned MCP dependencies + npm/PyPI freshness
python3 scripts/check_action_pins.py .github/workflows --remote  # verify SHA-pinned GitHub Actions comments
python3 scripts/check_plugin_hooks.py                      # verify plugin hook contract; forbids permission.ask as enforcement
python3 scripts/validate_contract.py                       # verify canonical rldyour adapter contract
python3 scripts/smoke_mcp_capabilities.py                  # probe every MCP server for reachability
python3 scripts/validate_instruction_docs.py               # verify AGENTS.md + .claude/CLAUDE.md anchor headings
bash scripts/doctor_opencode.sh                            # full diagnostics: MCP, LSP binaries, agent/skill/command discovery, git
bash scripts/check_lsps.sh                                 # 16 language servers + project prereqs
bash scripts/collect_diagnostics.sh --include-doctor       # local timestamped diagnostic bundle for triage
opencode debug config                                      # native resolved config (authoritative)
opencode debug agent <name>                                # validate individual agent
opencode models anthropic                                  # list available models for the active provider
```

Public repositories use automatic CI/CD by default. `opencode.json` loads
`references/public-repo-ci-policy.md` through `instructions`; keep
`share: "manual"` unchanged because it controls OpenCode session sharing, not
GitHub Actions execution.

CI mirrors the core checks via `.github/workflows/validate.yml` on every push/PR to `main`. `.github/workflows/dependency-check.yml` runs weekly to surface MCP pin freshness via `GITHUB_STEP_SUMMARY`.

See `docs/observability.md` for full triage flow.

## Convention

- User-facing communication: **Russian** by default.
- Repository artifacts (docs, prompts, scripts, commits, memories): **English**.
- Identifiers: ASCII, kebab-case.
- Commits: Conventional Commits v1.0.0; atomic per logical unit.
- Versioning: SemVer; CHANGELOG follows Keep a Changelog 1.1.0.
- Ignored agent-only files (`AGENTS.md`, `.claude/CLAUDE.md`, `.serena/memories/*`, etc.) are overlaid onto the current `HEAD` tree and published via the generated `fullrepo` branch managed by `scripts/fullrepo_sync.sh`.

## License

AGPL-3.0-or-later
