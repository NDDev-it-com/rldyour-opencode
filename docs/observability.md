# Observability

This repository uses lightweight operational observability: deterministic logs, failure artifacts, summaries, and local diagnostic bundles. There is no daemon, no metrics export, and no external telemetry service - the marketplace is single-developer and the diagnostic surface is intentionally local-first.

## What to check first

When something feels wrong:

- `git status -sb` - local repository state, branch, ahead/behind.
- `git log --oneline -20` - recent change history.
- `bash scripts/git_sync_audit.sh` - branch, upstream, dirty files, worktrees, merged-branch cleanup candidates.
- `bash scripts/validate_config.sh` - full repository-level validator (opencode.json schema, skill/agent/command frontmatter, VERSION semver).
- `bash scripts/flow_post_task_state.sh` - composite git / Serena / tracked-context / instruction-docs state in JSON.
- `python3 scripts/smoke_mcp_capabilities.py` - verify every declared MCP server in `opencode.json` is reachable.
- `python3 scripts/validate_instruction_docs.py` - verify `AGENTS.md` and `.claude/CLAUDE.md` are present, non-trivially large, and contain required anchor sections.
- `opencode debug config` / `opencode debug info` / `opencode debug agent <name>` / `opencode debug skill` - live native resolution from the OpenCode CLI.
- `gh run list --repo rldyourmnd/rldyour-opencode --limit 10` - latest CI state.

## Plugin-side observability

OpenCode plugins surface state through three channels:

| Channel | API | Visibility |
|---|---|---|
| Toast | `client.tui.showToast({ body: { variant, message }})` | User-visible banner in the TUI |
| App log | `client.app.log({ body: { service, level, message }})` | Server-side log file (`~/.local/share/opencode/log/*.log` on macOS/Linux) |
| Tool metadata | `ctx.metadata({ title, metadata: { ... }})` inside a custom tool | TUI tool card; the title is shown next to the tool call |

`console.log` lands only in the server log and is invisible to the user - every advisory message in this marketplace uses the three channels above. See `references/opencode-plugin-patterns.md` for the canonical patterns.

## Diagnostic bundle

To package the local state for triage:

```bash
bash scripts/collect_diagnostics.sh                  # minimal bundle
bash scripts/collect_diagnostics.sh --include-doctor # add LSP doctor + opencode doctor
```

The script writes a timestamped directory under `diagnostics/` (git-ignored). Typical contents:

| File | Source |
|---|---|
| `VERSION`, `CHANGELOG.md`, `opencode.json` | Repository state at the time of capture |
| `git-status.txt`, `git-log.txt`, `git-remote.txt`, `git-worktrees.txt` | Git metadata snapshot |
| `validate.log` | `bash scripts/validate_config.sh` output |
| `deps-pins.json` | `bash scripts/check_deps_freshness.sh --json` |
| `action-pins.txt` | `python3 scripts/check_action_pins.py .github/workflows` |
| `flow-state.json` | `bash scripts/flow_post_task_state.sh` |
| `git-audit.txt` | `bash scripts/git_sync_audit.sh` |
| `mcp-smoke.json` | `python3 scripts/smoke_mcp_capabilities.py --json` |
| `opencode-info.txt`, `opencode-config.txt` | `opencode debug info / config` (skipped if CLI absent) |
| `env.txt` | Runtime fingerprint: `uname -a`, shell, and `--version` of opencode / bun / uvx / python3 / node / git |
| `lsp-health.txt`, `doctor.txt` | LSP + opencode doctor (with `--include-doctor`) |

The bundle never contains `.env*`, credentials, or anything from `~/.ssh` / `~/.gnupg` / `~/.aws` (the `ry-env-protection` plugin would block the read at runtime). It is safe to attach to issues, gist, or share with a co-developer.

## CI observability

`.github/workflows/validate.yml` runs on every push and PR to `main`. It writes:

- Per-step output to the standard GitHub Actions log.
- A short summary in `GITHUB_STEP_SUMMARY` (file count of the marketplace).

`.github/workflows/dependency-check.yml` runs weekly (Monday 06:00 UTC) and on `workflow_dispatch`. It writes the pinned-dependency JSON envelope to `GITHUB_STEP_SUMMARY`, checks GitHub Actions SHA/comment integrity with `scripts/check_action_pins.py --remote`, and records the registry freshness probe so the owner can review pin freshness without cloning.

## Failure triage order

1. Read the failing GitHub Actions job summary.
2. Pull the diagnostic bundle: `bash scripts/collect_diagnostics.sh --include-doctor`.
3. Inspect `validate.log`, `opencode-config.txt`, `mcp-smoke.json`, and `flow-state.json`.
4. If MCP-related: check `mcp-smoke.json` for non-`alive` servers; rerun the local launcher manually.
5. If LSP-related: check `lsp-health.txt`; reinstall via `bash scripts/install_lsps.sh`.
6. If git-state-related: check `git-status.txt`; durable AI context is tracked on `main`, while runtime-local Serena state remains ignored.
7. Reproduce locally with the exact command that failed.

## Logging rules

- Never write secrets, raw credentials, cookies, or private tokens to logs.
- Plugin advice goes through `client.app.log` (structured) and optionally `client.tui.showToast` (user-visible).
- The `ry-command-audit` plugin sanitises every slash-command line through a credential-pattern stripper before writing to `.serena/.command_audit.log` (see `scripts/tests/test_command_audit_sanitizer.py` for the credential prefix coverage).
- Diagnostic bundles are filesystem-local; they are not uploaded automatically. The owner controls what to share.
