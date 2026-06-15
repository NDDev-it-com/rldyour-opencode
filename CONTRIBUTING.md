# Contributing to rldyour-opencode

Thanks for taking the time to contribute to the rldyour AI CLI configuration for OpenCode: local plugins, MCP/LSP, permissions, commands, agents, browser/design workflows, and security review. This document captures the workflow, validation contract, and reviewer expectations for code, configuration, documentation, and Serena memory changes in this OpenCode marketplace.

## Quick links

- Code of Conduct: [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- Security disclosure: [SECURITY.md](./SECURITY.md)
- Cross-tool root instructions: [AGENTS.md](./AGENTS.md) (agent-only, published to `fullrepo`)
- Architecture decisions: [docs/decisions/](./docs/decisions/)
- Release process: [docs/release-process.md](./docs/release-process.md)
- Observability triage: [docs/observability.md](./docs/observability.md)
- Reviewer protocol: [references/reviewer-protocol.md](./references/reviewer-protocol.md)

## Repository layout

The marketplace splits into two artifact classes:

| Class | What lives there | Branch |
|---|---|---|
| Normal-branch runtime | `opencode.json`, `README.md`, `VERSION`, `CHANGELOG.md`, `.env.example`, `scripts/`, `docs/`, `references/`, `.github/`, `.opencode/{agents,skills,commands,plugins}/` | `main` |
| Agent-only context | `AGENTS.md`, `.claude/CLAUDE.md`, `.serena/memories/*`, `.serena/project.yml` | `fullrepo` (orphan) |

The `fullrepo` branch is managed via `scripts/fullrepo_sync.sh`. Do not commit agent-only paths to `main` - they are excluded via `.git/info/exclude`.

## Local development setup

```bash
# Prerequisites: Python 3.13, Bun 1.2+, uvx (uv), bash, git
git clone https://github.com/NDDev-it-com/rldyour-opencode.git
cd rldyour-opencode

# Install plugin SDK dependencies (used by typecheck workflow)
cd .opencode && bun install --frozen-lockfile && cd ..

# Optionally bootstrap agent-only context from fullrepo
bash scripts/bootstrap_opencode.sh
bash scripts/fullrepo_sync.sh restore
```

## Validation contract

Before opening a PR, every change MUST pass these local gates. They mirror the CI workflows in `.github/workflows/`.

```bash
bash scripts/validate_config.sh                                          # opencode.json + frontmatter (strict YAML) + VERSION + action pins
uvx --from "pytest==9.0.3" --with "pyyaml==6.0.3" --with "jsonschema==4.26.0" --with "referencing==0.36.2" pytest scripts/tests/  # 500 passed + 1 skipped across 23 suites
bash scripts/check_deps_freshness.sh --check-freshness                   # pin report + registry freshness
python3 scripts/check_action_pins.py .github/workflows --remote          # SHA/comment integrity for actions
bunx --bun tsc --noEmit -p .opencode/tsconfig.json                       # plugin typecheck
uvx --from "ruff==0.15.13" ruff check scripts                            # python lint
```

When `opencode` CLI is on PATH, `validate_config.sh` also exercises the live `opencode debug config | skill | agent build` resolution smoke. CI runs the same scripts on Ubuntu and macOS matrices.

## Commit, branch, and PR conventions

- **Conventional Commits 1.0.0** for every commit. Format: `<type>(<scope>): <description>` with type from `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`.
- **Atomic commits**: one logical change per commit. Split unrelated implementation, tests/validators, docs/instructions, license/metadata, generated artifacts, and Serena/fullrepo sync when they are independently reviewable. Never `--amend` an already-pushed commit; ship a follow-up commit instead.
- **Commit subject ≤72 characters**; longer detail in the body.
- **Branch naming**: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`. Solo-maintainer commits on `main` are acceptable for small atomic changes; multi-step features should use a feature branch and a single PR.
- **PR description** must include: scope, validation evidence (which gates ran green), risk assessment, ADR link if architectural.

## Domain boundaries

The marketplace assigns each skill / agent / command / plugin to exactly one of 10 domains (see `AGENTS.md` § Domain Boundaries). Cross-domain logic is forbidden. The single exception is `.opencode/plugins/ry-tools.ts`, which intentionally bundles multi-domain diagnostic tools and documents the bundling intent in its file header.

## Reviewer subagent contract

When PRs are reviewed via `/ry-review` or `/ry-start`, six parallel reviewer subagents (`flow-architecture-review`, `flow-quality-review`, `flow-consistency-review`, `flow-integration-review`, `flow-verification-review`, `flow-security-review`) run read-only checks against the diff. See `references/reviewer-protocol.md` for the finding format and disposition rules.

## ADR policy

Architectural decisions follow MADR 4.0.0 in `docs/decisions/NNN-slug.md`. Add an ADR when:

- changing the source-of-truth contract for a file class,
- introducing a new domain or relaxing a domain boundary,
- changing release / packaging / governance defaults,
- adopting or removing a critical dependency,
- expanding or contracting the CI baseline.

ADR bodies are immutable. Update guidance through a supersession banner at the top of the file, not by rewriting history.

## Token and credential setup

The remote `github` MCP server reads `GITHUB_PERSONAL_ACCESS_TOKEN` from
the environment. Use a **fine-grained personal access token**, not a
classic PAT. Setup checklist:

1. Open GitHub → Settings → Developer settings → Personal access tokens
   → **Fine-grained tokens**.
2. Restrict the resource owner to a single account/org and scope the
   token to only the repositories the agent needs.
3. Grant only the minimum repository permissions the workflow expects
   (`Contents: Read`, `Pull requests: Read/Write` where the agent
   creates PRs). Read `docs/security/mcp-trust-boundaries.md` for the
   full read/write capability table per MCP.
4. Set an expiration ≤ 90 days. Rotate quarterly.
5. Set the `GITHUB_PERSONAL_ACCESS_TOKEN` variable in the same shell
   session that starts OpenCode (export it from your profile or pass
   it through your secret manager). Do NOT write the value into any
   tracked file - `.env*` is git-ignored and blocked at runtime by
   the `ry-env-protection` plugin.

Classic PATs are blocked by policy except for explicit short-term
troubleshooting; if you find one in use, file an issue and rotate. The
`ry-env-protection` plugin guards against reading `.env*` files at
runtime, but the durable defense is keeping the token out of the repo.

The same fine-grained-only policy applies to optional tokens for
`mcp.context7` (`CONTEXT7_API_KEY`) and `mcp.figma`. See
`docs/security/mcp-trust-boundaries.md` for the per-MCP trust class
matrix.

## Serena memory hygiene

Memory files at `.serena/memories/AREA-NN-SLUG.md` contain verified durable facts. Update them via `serena-memory-sync` or the `@flow-memory-sync` subagent. Do not write speculative notes, secrets, or runtime snapshots into memories. Use code, tests, and git history as the source of truth.

## What we won't accept

- Hacks, temporary workarounds, or untracked debt.
- Fake green checks. If a check cannot run, the PR must say so explicitly.
- Silent destructive git actions (force-push without lease, hard reset on shared branches, dropping branches without verified merged state).
- Secrets, credentials, tokens, cookies, or runtime markers in commits, logs, docs, or memories.
- `console.log` family in production plugin code (use `client.app.log` + `client.tui.showToast` per `references/opencode-plugin-patterns.md`).
- Cross-domain skill / agent / command bundling.
- New ADRs without the four MADR sections (Context, Considered Options, Decision Outcome, Consequences).

## Questions

- Operational: open a GitHub issue using the `config_question.md` template.
- Security: see [SECURITY.md](./SECURITY.md). Do not file public issues for vulnerabilities.
- Repository owner: `NDDev` (`rldyourmnd`), maintainer: `Danil Silantyev`.
