# rldyour-opencode

`rldyour-opencode` is the rldyour AI CLI configuration for OpenCode: local plugins, MCP/LSP, permissions, commands, agents, browser/design workflows, and security review.

[![validate](https://github.com/NDDev-it-com/rldyour-opencode/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/NDDev-it-com/rldyour-opencode/actions/workflows/validate.yml)
[![CodeQL](https://github.com/NDDev-it-com/rldyour-opencode/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/NDDev-it-com/rldyour-opencode/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/NDDev-it-com/rldyour-opencode/badge)](https://scorecard.dev/viewer/?uri=github.com/NDDev-it-com/rldyour-opencode)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Latest Release](https://img.shields.io/github/v/release/NDDev-it-com/rldyour-opencode)](https://github.com/NDDev-it-com/rldyour-opencode/releases/latest)

`rldyour-opencode` is the rldyour AI CLI configuration for OpenCode: local TypeScript plugins, MCP/LSP, permissions, slash commands, subagents, browser/design workflows, and security review. Russian-first SDLC workflow, Serena integration, full-auto owner posture - all native to the OpenCode AI coding agent format.

## Current Baseline

| Field | Value |
|---|---|
| Adapter version | `1.7.12` |
| Runtime baseline | OpenCode 1.17.13 |
| GitHub release tag | `1.7.12` |

Runtime baseline source: `references/opencode-baseline.json`. Submodule pins are owned by the root control-plane `config/repositories.json`.

Validated against `opencode-ai`, `@opencode-ai/plugin`, and `@opencode-ai/sdk` 1.17.13 (June 2026). The v1.14.48 → v1.17.13 jump preserves the runtime hook surface and tool-ID naming while picking up current plugin-loading, skill discovery and file-based agent loading, `run --replay`, ACP/WebSocket runtime fixes, provider-compatible reasoning summaries, safer edit matching, backgroundable subagents, session context persistence, and permission reply routing fixes. The `1.17.13` config schema is byte-identical to the `v1.17.7` snapshot (SHA-256 `57c02429`).

## What This Repository Provides

`rldyour-opencode` is a self-contained OpenCode project configuration package - not a fork of the OpenCode runtime. Drop `opencode.json` and `.opencode/` into any project and OpenCode resolves the full configuration: 38 skills across 10 workflow domains, 9 subagents, 11 slash commands, 10 TypeScript plugins, 11 MCP servers, 8 custom LSP servers, and owner-standard full-auto permissions. The adapter is authored by Danil Silantyev (github:rldyourmnd), CEO NDDev, and is licensed under AGPL-3.0-or-later. Implementation changes belong in this repository; the control-plane superproject (`rldyour-ai-cli-tools`) only advances the submodule pin.

## Native Boundaries

OpenCode's native config surfaces that this adapter populates:

- **Master config**: `opencode.json` (JSON or JSONC) - model, MCP, LSP, agents, watchers, compaction, permission rules.
- **Release-safe overlay**: `opencode.release-safe.json` - conservative static read-deny patterns for `.env`, private keys, tokens, and shell/edit ask posture for public OSS examples.
- **Durable AI context**: `AGENTS.md`, `.opencode/`, `.serena/project.yml`, and `.serena/memories/` are tracked on `main`. Runtime-local Serena state remains ignored.
- **`.opencode/` directory layout**:
  - `agents/*.md` - 9 subagents (6 reviewer tracks, memory-sync, ry-explore, customize-opencode)
  - `skills/<name>/SKILL.md` - 38 skills across 10 domains
  - `commands/*.md` - 11 slash commands
  - `plugins/*.ts` - 10 Bun-runtime TypeScript local plugins
  - `package.json` - `@opencode-ai/plugin` pin for local Bun dependency resolution
- **Permission keys (canonical v1.17.13)**: `read`, `edit`, `bash`, `task`, `external_directory`, `doom_loop` - used in `opencode.json` `permission.*` fields.
- **MCP JSON**: declared under `mcp` in `opencode.json`; local servers use `bunx` (npm) or `uvx` (Python) or `dart` (Dart SDK) launchers - never `npx`.

Source-only artifacts (scripts, tests, CI workflows, reference docs, ADRs) are not loaded by OpenCode at runtime; they exist for validation and release hygiene only.

## Install / Update / ry-repair

**Install** - clone and copy into your project:

```bash
git clone https://github.com/NDDev-it-com/rldyour-opencode.git
cd rldyour-opencode
cp opencode.json /path/to/your/project/opencode.json
cp -r .opencode /path/to/your/project/.opencode
cp AGENTS.md /path/to/your/project/AGENTS.md
```

**Authenticate** - log in to your provider interactively, then set any required MCP env vars:

```bash
opencode auth login
export GITHUB_PERSONAL_ACCESS_TOKEN=YOUR_PLACEHOLDER_TOKEN  # required for GitHub MCP
export CONTEXT7_API_KEY=YOUR_PLACEHOLDER_KEY               # optional
```

**Run**:

```bash
cd /path/to/your/project
opencode
```

**Check resolved config** (authoritative):

```bash
opencode debug config
```

**Diagnose runtime** (MCP, LSP binaries, agent/skill/command discovery, git):

```bash
bash scripts/doctor_opencode.sh
```

**Owner launcher** (`oc`) - the `rldyour-ai-cli-tools` root provides `scripts/install_yolo_launchers.sh --apply`, which installs the `oc` wrapper that injects an allow-all `OPENCODE_CONFIG_CONTENT` override and sets `OPENCODE_DISABLE_CLAUDE_CODE=1` so root skill resolution uses `.opencode/skills`. Use `oc` for the trusted owner workstation full-auto posture.

**Convergence** - inside any project where this config is active, run `/ry-repair` to repair stale docs, memories, contracts, hooks, MCP/LSP config, CI, and AI-tool context.

**Update** - pull the latest adapter tag, re-copy `opencode.json` and `.opencode/`, then run `opencode debug config` to confirm runtime resolved correctly. Check `CHANGELOG.md` and `references/opencode-baseline.json` for any dependency bumps that require re-authentication or pin updates.

## Active Catalog

| Layer | Where | Count |
|---|---|---|
| Master config | `opencode.json` | 1 |
| Release-safe overlay | `opencode.release-safe.json` | 1 |
| Cross-tool instructions | `AGENTS.md` | 1 |
| Claude Code project memory (agent-only) | `.claude/CLAUDE.md` | 1 |
| Subagents | `.opencode/agents/*.md` | 9 |
| Skills | `.opencode/skills/<name>/SKILL.md` | 38 |
| Slash commands | `.opencode/commands/*.md` | 11 |
| Plugins | `.opencode/plugins/*.ts` | 10 |
| Custom diagnostic tools (LLM-callable) | `.opencode/plugins/ry-tools.ts` | 5 |
| MCP servers | `opencode.json` → `mcp` | 11 |
| Custom LSP servers | `opencode.json` → `lsp` | 8 |
| Reference docs (contracts + machine metadata) | `references/*` | 22 |
| Operator guides | `docs/*.md` | 5 |
| Architecture decision archive | `docs/decisions/*.md` | 10 |
| Diagnostic scripts (bash + Python) | `scripts/` | 30 |
| Pytest suites | `scripts/tests/*.py` | 26 |
| CI workflows | `.github/workflows/*.yml` | 11 |

### Slash Commands

| Command | Agent | Purpose |
|---|---|---|
| `/ry-init` | `build` | Scoped read-only project context with Serena-first discovery |
| `/ry-start` | `build` | Full task lifecycle: init → research → plan → implement → verify → sync |
| `/ry-review` | `plan` | Report-only deep review with parallel reviewer subagents |
| `/ry-repair` | `build` | Repair stale docs, memories, contracts, hooks, MCP/LSP config, CI, and AI-tool context |
| `/ry-newp` | `build` | Plan a new project (skeptical questions, research, ADRs, architecture docs) |
| `/ry-deploy` | `build` | Deploy with sync, log checks, fix-forward |
| `/ry-sync` | `build` | Synchronize memories, docs, git, and tracked context |
| `/ry-design` | `build` | End-to-end design: Figma → tokens → FSD → shadcn/ui → browser validation |
| `/ry-explore` | `ry-explore` (subtask) | Deep multi-source research via Context7 / DeepWiki / Grep / web |
| `/ry-sec-review` | `plan` | Defensive Mythos-style security review |
| `/ry-rules-review` | `plan` | Audit implementation against rldyour rules (report-only) |

### MCP Servers

Local servers timeout 30 s, remote 15 s. Launcher convention: `bunx` for npm, `uvx` for Python, `dart` for Dart SDK.

| Server | Type | Version | Purpose |
|---|---|---|---|
| serena | local (uvx) | 1.5.3 | Semantic code navigation, analysis, editing |
| sequential-thinking | local (bunx) | 2025.12.18 | Structured reasoning |
| chrome-devtools | local (bunx) | 1.5.0 | Chrome DevTools diagnostics |
| shadcn | local (bunx) | 4.13.0 | shadcn/ui registry access |
| dart-flutter | local (dart) | - | Dart/Flutter project support |
| context7 | remote | - | Current library documentation |
| deepwiki | remote | - | Repository documentation |
| grep | remote | - | Search across public GitHub repos |
| figma | remote | - | Figma design context |
| github | remote | toolsets: context,repos,issues,pull_requests,users | Remote GitHub MCP endpoint (requires PAT) |
| openai-docs | remote | - | Official OpenAI/Codex documentation |

### TypeScript Plugins

10 Bun-runtime plugins loaded from `.opencode/plugins/*.ts`:

- **Lifecycle**: `ry-bootstrap` (session banner + compaction context + autocontinue), `ry-env-protection` (block sensitive reads with toast), `ry-shell-strategy` (shell env + git push guardrails), `ry-sync-reminder` (idle toast), `ry-flow-hooks` (commit advice + post-commit nudge).
- **LLM-side**: `ry-tools` (5 custom diagnostic tools the LLM can call), `ry-command-audit` (credential-sanitized slash-command audit log), `ry-tool-hints` (routing nudges injected into MCP tool descriptions).
- **Runtime context + permission events**: `ry-system-context` (date + branch + HEAD SHA + dirty state injected into every system prompt), `ry-permission-events` (observability-only `permission.asked` / `permission.replied` event audit).

### LSP Servers

8 custom LSP servers on top of OpenCode's 35+ built-ins: `ruff`, `vscode-html`, `vscode-css`, `vscode-json`, `docker`, `taplo`, `marksman`, `qmlls`.

### Models

The marketplace ships with `opencode-go/glm-5.1` as the top-level default. Subagents inherit the top-level model.

| Slot | Default in this repo | Common Anthropic alternative |
|---|---|---|
| `model` (primary) | `opencode-go/glm-5.1` | `anthropic/claude-sonnet-4-6` |
| `small_model` | `opencode-go/glm-5.1` | `anthropic/claude-haiku-4-5-20251001` |
| `default_agent` | `build` | `build` |
| Reviewer / memory-sync / explore subagents | inherit top-level `model` | inherit top-level `model` |

Run `opencode models <provider>` to list every accepted ID. To switch provider, edit `"model"` in `opencode.json` and confirm with `opencode debug config`.

## Browser / Design / DevTools Routing

Three browser providers are active, each with a distinct role:

- **Webwright skill** - long-horizon or reusable web workflows, multi-step task automation, and web research tasks where a persistent browser session adds value.
- **Playwright CLI** - UI evidence collection: screenshots, snapshots, traces, visual diffs, and page-state assertions. Invoke via the `playwright-cli` skill.
- **Chrome DevTools MCP** (`chrome-devtools`, version 1.5.0) - DevTools-level diagnosis: console messages, network requests, heap snapshots, performance traces, Lighthouse audits, and memory profiling. Use when you need browser internals rather than just page screenshots.

The `/ry-design` command routes through Figma MCP (design context and asset download), shadcn/ui MCP (registry access), and Chrome DevTools MCP (validation). DeepWiki, Context7, and Grep MCP support research and documentation retrieval during design and exploration tasks.

## Repository Context / Serena Memory

Normal `main` history carries product artifacts and durable agent context:
`opencode.json`, `.opencode/`, `AGENTS.md`, `.serena/project.yml`,
`.serena/memories/*.md`, scripts, tests, CI workflows, docs, and reference
files.

Serena memories live under `.serena/memories/` using the `AREA-NN-SLUG.md`
taxonomy. The freshness contract: memories are updated only from verified
current code, git diffs, and tests - never from speculation, plans, or chat
history. Runtime-local cache, reviews, diagnostics, markers, local env files,
browser artifacts, tokens, cookies, and credentials stay ignored.

## Security Boundary

Owner full-auto posture is intentional and explicitly acknowledged. The primary `build` and `plan` agents use OpenCode's canonical v1.17.13 permission keys with `"allow"` for `read`, `edit`, `bash`, `task`, `external_directory`, and `doom_loop`. This is not a sandbox - it is a trusted owner workstation posture designed for maximum autonomy.

The `oc` launcher (from `scripts/install_yolo_launchers.sh --apply`) injects an allow-all `OPENCODE_CONFIG_CONTENT` environment override and sets `OPENCODE_DISABLE_CLAUDE_CODE=1`, mirroring the same no-prompt posture at the OS launcher level.

Reviewer subagents are explicitly stricter: `edit: "deny"`, `bash` allowlists limited to read-only git verbs. Their role contract is report-only review, not implementation.

The `ry-env-protection` plugin blocks reads of `.env`, private key files, tokens, and credentials with a toast notification before the LLM sees them. The `opencode.release-safe.json` overlay provides a conservative alternative profile for public OSS examples and cautious installs.

MCP secrets (`GITHUB_PERSONAL_ACCESS_TOKEN`, `CONTEXT7_API_KEY`, etc.) are passed as environment variables and are never committed. Use `.env.example` as a reference; never populate `.env` with real values in version control. Security vulnerabilities should be reported via GitHub Security Advisories - do not file public issues.

## Validation

```bash
bash scripts/validate_config.sh                            # JSON shape + skill/agent/command frontmatter + VERSION semver
uvx --from "pytest==9.1.1" --with "pyyaml==6.0.3" --with "jsonschema==4.26.0" --with "referencing==0.37.0" pytest scripts/tests/
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

CI mirrors core checks via `.github/workflows/validate.yml` on every push/PR to `main`. `.github/workflows/dependency-check.yml` runs weekly to surface MCP pin freshness. Public repositories use standard GitHub-hosted runners; keep `share: "manual"` unchanged (it controls OpenCode session sharing, not CI execution). See `docs/observability.md` for the full triage flow.

Commands marked NOT_PROVEN (e.g., live MCP probes) require network access and installed binaries; skip them in offline or CI-only environments.

## Release / Rollback

Releases are tag-driven. Every product version must have a matching numeric GitHub Release at `github.com/NDDev-it-com/rldyour-opencode/releases`. A `VERSION` file update alone is not sufficient.

Version movement follows the control-plane policy: default is patch (`+0.0.1`) after a public release exists; minor and major bumps are owner-directed decisions only. `CHANGELOG.md` follows Keep a Changelog 1.1.0. `SECURITY.md` lists the exact supported version tag.

**Rollback**: to revert to a prior release, check out the numeric tag (`git checkout X.Y.Z`), re-copy `opencode.json` and `.opencode/` into your project, and re-run `opencode debug config`. See `docs/rollback-restore.md` for the full rollback and restore procedure. Dependency update policy is in `docs/dependency-updates.md`.

## Support / License

- **License**: AGPL-3.0-or-later
- **Author**: Danil Silantyev (github:rldyourmnd), CEO NDDev
- **Issues**: [github.com/NDDev-it-com/rldyour-opencode/issues](https://github.com/NDDev-it-com/rldyour-opencode/issues) - bug reports, regression evidence, missing-component requests.
- **Discussions**: [github.com/NDDev-it-com/rldyour-opencode/discussions](https://github.com/NDDev-it-com/rldyour-opencode/discussions) - general questions, workflow advice, configuration clarifications, sharing usage patterns.
- **Releases**: [github.com/NDDev-it-com/rldyour-opencode/releases](https://github.com/NDDev-it-com/rldyour-opencode/releases) - numeric product tags (`X.Y.Z`) with release notes from CHANGELOG.
- **Security**: Report vulnerabilities via [GitHub Security Advisories](https://github.com/NDDev-it-com/rldyour-opencode/security/advisories) - do not file public issues for security vulnerabilities.

This is a personal marketplace - response time is best-effort, no SLA. Feel free to fork and tailor to your own workflow.
