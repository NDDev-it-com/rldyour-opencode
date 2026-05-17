# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.11.1] - 2026-05-18

Patch stabilization pass closing the deferred 0.11.0 reviewer findings that were below the release-blocking threshold. The patch tightens parser fidelity, dependency freshness ordering, and plugin advisory coverage without changing public marketplace layout.

### Fixed

- **`scripts/_validate_helpers.py` duplicate-key detection** now uses `yaml.compose` node traversal after strict `yaml.safe_load`, so quoted duplicate top-level keys (for example `"name"` repeated twice) are rejected by the same YAML parser surface that loads the frontmatter. The old regex pass only caught unquoted `key:` lines.
- **`scripts/_check_freshness.py` prerelease ordering** now compares `(major, minor, patch, stability)` tuples, with stable releases sorted above matching `dev` / `rc` / `alpha` / `beta` / `preview` / `nightly` / `snapshot` builds. `1.3.0.dev0` vs `1.3.0` now reports `stale`; the inverse reports `ahead`.
- **`.opencode/plugins/ry-env-protection.ts` command tokenization** now preserves literal backslashes inside path tokens. Escaped shell paths keep enough information for `isSensitivePath()` instead of being split before inspection.
- **`.opencode/plugins/ry-shell-strategy.ts` destructive-rm advisory** now warns for bare recursive build-output targets such as `rm -rf build` / `rm -rf dist`; `node_modules` cleanup remains the explicit non-catastrophic warning allowlist.

### Changed

- `VERSION` bumped to `0.11.1`.
- `.github/workflows/codeql.yml` now loads `.github/codeql/codeql-config.yml`, explicitly scanning `.opencode/plugins`, `scripts`, and workflow files. This prevents the JavaScript/TypeScript CodeQL job from seeing only workflow YAML while missing plugin sources under the hidden `.opencode/` directory.
- `.github/workflows/codeql.yml` now grants `actions: read` alongside `security-events: write`, matching the CodeQL Action private-repository SARIF upload requirement.
- `.github/workflows/validate.yml` now installs the pinned PyYAML dependency before invoking `scripts/validate_config.sh`; live GitHub runners do not carry PyYAML by default.
- `.github/workflows/secret-scan.yml` now installs the `gitleaks` v8.30.1 CLI directly from the official release tarball with SHA256 verification, avoiding the organization/private-repository license gate in `gitleaks/gitleaks-action`.
- `.gitleaks.toml` allowlists only the synthetic sanitizer regression fixture files that intentionally contain fake token/private-key strings; the workflow still scans git history for every other path.
- `README.md`, `AGENTS.md`, `.claude/CLAUDE.md`, and Serena release memories refreshed from the 0.11.1 validation baseline.
- Corrected the 0.11.0 changelog test-count line from stale intermediate numbers to the final `7c02482` collection state.

### Test coverage

- Total pytest cases: **372** across 13 suites (was 357 at `7c02482`, +15). Breakdown: 52 validate_helpers + 12 extract_pins + 129 skill_routing + 16 command_audit_sanitizer + 11 plugin_surface + 4 opencode_resolve + 44 permission_policy_regexes + 11 smoke_mcp + 7 validate_instruction_docs + 8 doctor_opencode + 23 sanitize_diag + 40 check_freshness + 15 fullrepo_sync.

## [0.11.0] - 2026-05-17

Audit-driven stabilization pass closing every P0/P1 finding from four parallel external audits (ChatGPT 5.5 Pro prompt + three deep-audit reports). Closes a class of silent regex-only validation failures, completes defense-in-depth coverage at the unconditional layer, removes dead Project casts, refreshes drift between stale counts/pointers and HEAD facts, expands CI baseline to Ubuntu + macOS matrix, adds governance scaffolding, and ships three new ADRs.

### Fixed

- **CRITICAL — strict YAML frontmatter validation (`scripts/_validate_helpers.py`).** Replace regex-based `_yaml_top_key` / `_yaml_block_child_keys` with `yaml.safe_load`. The regex parser silently accepted 6 reviewer agent frontmatter files whose `description:` line contained an unquoted second colon (e.g. `description: Orchestrated architecture review: boundaries, ...`) — invalid YAML under any standards-conformant 1.2 implementation. PyYAML 6.0.3 is now a hard dependency of the validator; CI installs it via `uvx --with pyyaml==6.0.3`.
- **CRITICAL — quote 6 reviewer agent descriptions** (`flow-architecture-review`, `flow-consistency-review`, `flow-integration-review`, `flow-quality-review`, `flow-security-review`, `flow-verification-review`) so the same content parses as a YAML scalar instead of triggering a mapping-values-not-allowed error.
- **`scripts/_validate_helpers.py::validate_opencode_json`** now catches `FileNotFoundError` gracefully and reports a deterministic `[ERR]` line instead of an unhandled traceback when the manifest is missing.
- **`scripts/_validate_helpers.py::validate_agent`** now accepts `mode: all` per OpenCode v1.15.x docs alongside `primary` and `subagent`. Previously rejected as an unknown mode — would have broken any future config that uses the `all` mode default documented at https://opencode.ai/docs/agents.
- **`scripts/_validate_helpers.py::validate_skill`** now explicitly rejects the eight Claude Code / Codex residue fields (`allowed-tools`, `disable-model-invocation`, `model`, `effort`, `maxTurns`, `paths`, `context`, `agent`) listed as forbidden in `AGENTS.md` skill rules. Previously silent.
- **HIGH — `.opencode/plugins/ry-shell-strategy.ts` defense-in-depth completion**. Add unconditional `tool.execute.before` throws for two patterns previously only caught by `permission.ask` (which fires only when bash permission is statically `"ask"` — not `"allow"` as the Build agent uses globally): (a) catastrophic `rm -rf` targeting root / `$HOME` / `~` / cwd with `node_modules` cleanup as the explicit allowlist exception; (b) `git push --no-verify` on `main`/`master`/`release`/`production` branches. Both throws now `log("error")` BEFORE the toast and throw, so the audit trail records the block reason even if the TUI toast call fails silently. Same hardening applied to the existing force-push throw.
- **HIGH — `.opencode/plugins/ry-bootstrap.ts` dead Project cast**. Replace hand-rolled `project as { name?: string; path?: string }` cast with the typed `project.worktree` field from `@opencode-ai/sdk` `Project` (gen/types.gen.d.ts:607). Neither `name` nor `path` are typed Project fields; `name` is derived from the basename of `worktree` instead.
- **`.opencode/plugins/ry-env-protection.ts`** widens bash secret-read detection from `cat|head|tail|less|more|type` only to also cover `grep|sed|awk|strings|xxd|od|hexdump|cut` (text and binary dumpers), `bat|view|nano|vim|vi|emacs` (pagers and editors), one-liner script execs (`python3 -c`, `node -e`, `ruby|perl|bash|sh|fish|zsh -[ce]`), and shell redirects (`< secrets.env`). Path detection now reuses the existing `isSensitivePath()` function so the `.env.example`/`.template`/`.sample` allowlist is honoured uniformly across `read` and `bash` tool blocks.

### Added

- **(group F)** Wire network-backed dependency freshness in `scripts/check_deps_freshness.sh` with `--check-freshness` flag, per-pin timeout, npm view + PyPI JSON API. JSON envelope extended with `latest`, `stale`, `source` fields.
- **(group F)** Add `.serena/.command_audit.log` to `scripts/fullrepo_sync.sh::RUNTIME_EXCLUDE_PATTERNS` (mirrors the project-root `.gitignore` rule installed in 0.10.0).
- **(group F)** Widen `scripts/fullrepo_sync.sh` secret-scan to all text files (Python `.py`, plain `.log`, no-extension files) using `grep -rI`; previous coverage missed Python tests and runtime logs.
- **(group F)** JSON-escape `scripts/fullrepo_sync.sh status-json` output via Python helper (`json.dumps`) instead of heredoc interpolation; previously could produce malformed JSON when a branch name contained `"` or `\`.
- **(group G)** New pytest suites: `test_fullrepo_sync.py` (publish/status/restore paths), `test_sanitize_diag.py` (every ordered redaction pattern), `test_check_deps_freshness.py` (envelope + flags). Extension of `test_validate_helpers.py` with strict YAML + FileNotFoundError + `mode: all` + forbidden-skill-field cases.
- **(group H)** `.opencode/tsconfig.json` strict-mode plugin config + baseline `bunx tsc --noEmit`.
- **(group I)** Expanded CI baseline — `validate.yml`, `dependency-check.yml`, `instruction-docs-check.yml`, `typecheck-plugins.yml`, `lint.yml` (ruff), `codeql.yml`, `secret-scan.yml` (gitleaks), `dependency-review.yml`, `release.yml`, `sbom.yml`. All actions pinned to commit SHA, `permissions: contents: read` per workflow, `concurrency` cancel-in-progress groups, explicit `timeout-minutes`. Ubuntu + macOS matrix for `validate`, `typecheck-plugins`, `lint`. CodeQL / gitleaks / dependency-review / SBOM stay Ubuntu-only (platform-independent). `.github/dependabot.yml` for weekly npm and github-actions ecosystem updates.
- **(group J)** Governance scaffolding: `CONTRIBUTING.md`, `SECURITY.md` (private disclosure route), `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `.github/CODEOWNERS`, `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/{bug_report,feature_request,config_question}.md`.
- **(group K)** Three new ADRs (MADR 4.0.0): `005-fullrepo-snapshot-boundary.md` (declares two artifact classes: normal-branch checkout vs `fullrepo` agent-only snapshot, with snapshot-aware validation), `006-defense-in-depth-complete.md` (`tool.execute.before` unconditional + `permission.ask` deny-only, with mandatory test-side coverage for force-push / catastrophic rm / `--no-verify`), `007-ci-mirrors-local-validation.md` (local scripts are the source of truth, CI is thin wrappers; SHA-pinned actions, least-privilege permissions, concurrency groups).

### Changed

- **`AGENTS.md`** validation command line refreshed (259/9 -> 282/10, PyYAML pin added to `uvx` env). Permission keys section replaces incomplete 14-key list with full 17-key canonical set (v1.15.x JSON Schema), cites `sst/opencode#15507` silent-acceptance risk.
- **`README.md`** pytest count table: 9/259 -> 10/282 with new `doctor_opencode` suite. Project structure block: 9 -> 10 suites. Models block: surface the real default (`opencode-go/glm-5.1`) plus Anthropic alternatives in a two-column table; document the `opencode debug config | grep` runtime smoke for verifying resolved model after switching providers.
- **`.claude/CLAUDE.md`** catalog row counts: 9/259 -> 10/282, repo version 0.10.1 -> 0.11.0. Validation cookbook: PyYAML pin in `uvx` invocation. Broken pointer `CORE_00_memory_index.md` -> `CORE-01-INDEX.md`.
- **All 4 ADR supersession banners** (`docs/decisions/001..004`): broken pointer `CORE_02_opencode_config.md` -> `CORE-02-PROJECT-SHAPE.md` (file referenced never existed under that underscore-style name; current taxonomy uses `AREA-01-SLUG.md`).
- **`references/opencode-plugin-patterns.md`** removes the dead `project as { name?, path? }` cast guidance.
- **`.serena/memories/*`** synchronized to HEAD facts: `CORE-01-INDEX.md`, `RELEASE-01-VALIDATION.md`, `TECHDEBT-01-NOW.md`, `CODEX-01-PLUGIN-CANON.md` updated with new pytest suite count, version bump, resolved-pattern entries for groups A-D.

### Test coverage

- Total pytest cases: **357** (was 282 at HEAD `1e14c22`, +75). Suite breakdown across 13 suites: 50 validate_helpers + 12 extract_pins + 129 skill_routing + 16 command_audit_sanitizer + 9 plugin_surface + 4 opencode_resolve + 44 permission_policy_regexes + 11 smoke_mcp + 7 validate_instruction_docs + 8 doctor_opencode + 23 sanitize_diag (new) + 29 check_freshness (new) + 15 fullrepo_sync (new).

## [0.10.1] - 2026-05-14

Hardening pass closing every deferred item from the 0.10.0 reviewer round (Architecture H-1..L-3, Verification C-1, H-1..H-3, M-1..M-5). Repairs a silent-broken regex class that affected the security-critical permission-ask and tool-execute layers, redacts secrets from diagnostic bundles, sharpens MCP smoke semantics, and lifts pytest coverage by 65 cases.

### Fixed

- **CRITICAL — flag-boundary regex repair (`ry-permission-policy.ts`, `ry-shell-strategy.ts`)**. The regex `\b--force\b` and its siblings `\b--force-with-lease\b` / `\b--no-verify\b` silently match nothing on real input: `\b` does not assert at a position where both adjacent characters are non-word (space then `-`). As a result the `permission.ask` layer never denied a force-push (always defaulted to "ask") and the `tool.execute.before` layer in `ry-shell-strategy.ts` threw on the SAFE `--force-with-lease` form because the whitelist regex never matched. Replace with a flag-boundary lookbehind/lookahead pair `(?<![A-Za-z0-9-])--force(?![A-Za-z0-9-])` that matches `--force` but not `--force-with-lease`, plus `/i` flag so `--FORCE` is also caught.
- **`ry-permission-policy.ts` product-branch alternation**. The flat form `\bmain|master|release|production\b` parsed as four alternatives with mismatched word boundaries, so `mainline` / `mainframe` / `productionish` were false-positively denied. Group as `\b(main|master|release|production)\b` so the boundaries apply uniformly.
- **`ry-permission-policy.ts` force-push short form**. Add `-f` short form (`(?:^|\s)-f(?:\s|$)`) alongside `--force`. Previously only `--force` was caught.
- **`scripts/collect_diagnostics.sh` secrets-in-bundle**. `opencode debug config` substitutes real env tokens (CONTEXT7_API_KEY `ctx7sk-*`, GITHUB_PERSONAL_ACCESS_TOKEN `gho_*` / `ghp_*`, ANTHROPIC_API_KEY `sk-ant-*`) into its JSON output. The diagnostics bundle copied that verbatim, leaving secrets on disk in `diagnostics/` (git-ignored but local-readable). Route every `run_cmd` output through a new `scripts/_sanitize_diag.py` stripper covering the vendor prefix set used by the marketplace; bundle is now secret-free by construction.
- **`scripts/smoke_mcp_capabilities.py` false-alive on fast clean exit**. `probe_local` classified `exit_code=0` inside the probe window as `alive`; a launcher that prints `--help` or a version banner and exits 0 would therefore pass the smoke. Tighten to "only `TimeoutExpired` (still running) proves alive; clean fast exit is `indeterminate`; non-zero exit is `fail`." Local result against the current 13-server marketplace: 6 indeterminate (chrome-devtools, dart-flutter, playwright, sequential-thinking, serena, shadcn — all exit 0 on stdin EOF), 0 failed.

### Added

- **`scripts/_sanitize_diag.py`** — credential-pattern stripper. Mirrors `.opencode/plugins/ry-command-audit.ts::sanitizeArgs` plus a Context7 entry for `ctx7sk-` and an Anthropic entry for `sk-ant-`. Does NOT enable the fallback opaque-32-char redactor (false-positive on commit SHAs and dependency-pin strings present in diagnostic bundles). Pattern order is more-specific-first; the generic `sk-` pattern uses a negative-lookbehind word boundary so order regressions cannot leak inside a longer compound prefix (e.g. `ctx7sk-`).
- **`scripts/tests/test_permission_policy_regexes.py`** (44 cases) — Python mirror of every regex in `ry-permission-policy.ts` with positive + negative + edge cases (force-push `--force` / `--FORCE` / `--force=true` / `-f`; safe `--force-with-lease`; rm -rf `/` / `$HOME` / `~` / `~/` / `.`; rm node_modules cleanup allowlist; safe `~/specific-subdir` and `./scoped/path`; --no-verify on main/master/release/production; --no-verify on feature/mainline/mainframe/productionish). Includes a lockstep guard that fails if the TS source and Python mirror diverge.
- **`scripts/tests/test_smoke_mcp.py`** (11 cases) — self-tests for `smoke_mcp_capabilities.py`: probe_remote HEAD success, HTTP-error-still-alive (401/403/405), HEAD-then-GET fallback, total network failure → fail; probe_local skip on missing launcher, alive on timeout, indeterminate on `true`, fail on `false`; main() exit codes 0 / 1 and --json envelope shape.
- **`scripts/tests/test_validate_instruction_docs.py`** (7 cases) — self-tests for `validate_instruction_docs.py`: missing file / too-short file / missing heading / all-good check_doc paths; main() exit codes; --json envelope shape using `tmp_path` so the real `AGENTS.md` and `.claude/CLAUDE.md` are untouched.
- **`scripts/tests/test_plugin_surface.py`** — 3 new structural tests (Verification M-3 + H-1 + H-3): `test_no_console_log_in_plugin_production_code` enforces the 0.10.0 migration to `client.app.log` + `client.tui.showToast`; `test_ry_tool_hints_dispatch_path_wired` proves the `tool.definition` hook reaches `output.description`; `test_ry_system_context_injects_runtime_fields` proves the runtime line carries date/branch/head/worktree with `"unknown"` fallback.
- **`.github/workflows/dependency-check.yml` smoke step** — runs `smoke_mcp_capabilities.py --json` in the weekly cron and publishes the envelope to `GITHUB_STEP_SUMMARY`. `continue-on-error: true` keeps a transient network failure from blocking the workflow; the summary still surfaces the outage for review.

### Changed

- **`scripts/tests/test_opencode_resolve.py`** hardened against pytest stdout-capture truncation (Verification C-1). `test_debug_skill_count_matches_directory` deterministically failed in isolation under default pytest capture (the 143 KiB `opencode debug skill` JSON gets truncated mid-string before the regex scan). Replaced with `test_debug_skill_resolves_cleanly` — head-substring probes for `"name"` and `"description"` keys; let `test_plugin_surface.py::test_all_expected_plugins_exist` enforce the actual count on disk. `test_debug_config_resolves_cleanly` adds a `"default_agent"` probe and drops the `"compaction"` probe (the latter lives past 4 KiB after the LSP block).
- **`scripts/smoke_mcp_capabilities.py` output**. New `indeterminate` status + `[?]` glyph + counter in both text and JSON output. Exit code stays 0 unless something genuinely failed.

### Test coverage

- Total pytest cases: **259** (was 194). Breakdown: 27 validate_helpers + 12 extract_pins + 129 skill_routing + 16 command_audit_sanitizer + 9 plugin_surface + 4 opencode_resolve + 44 permission_policy_regexes + 11 smoke_mcp + 7 validate_instruction_docs.

## [0.10.0] - 2026-05-13

OpenCode v1.14.48 best-practice uplift driven by a multi-source research pass (Context7 + DeepWiki + Grep MCP + opencode.ai docs + community marketplaces). Closes the hook-coverage gap, fixes a critical tool-ID format regression, hardens reviewer subagents, ships infrastructure for ongoing freshness checks, and brings every advisory message into the TUI.

### Added

- **`.opencode/plugins/ry-permission-policy.ts`** — new `permission.ask` deny-only policy plugin. Blocks `git push --force` without `--force-with-lease`, catastrophic `rm -rf` targets (root, $HOME, ~/, cwd; allowlists `node_modules` cleanup), and `git push --no-verify` on main/master/release/production. Never auto-allows; preserves user consent on legitimate prompts.
- **`.opencode/plugins/ry-system-context.ts`** — new `experimental.chat.system.transform` plugin injecting today's date, current git branch, HEAD short SHA, and dirty-tree status into every system prompt. Fixes "what day is it / what branch are we on" classes of LLM grounding errors that static AGENTS.md cannot address.
- **`ry-bootstrap.ts` `experimental.compaction.autocontinue` hook** — disables the synthetic "continue" turn that OpenCode injects after a context-overflow auto-compaction. Reviewer / security / sync agents typically produce a final report; an auto-continue turn either re-does the work or generates empty filler.
- **`scripts/smoke_mcp_capabilities.py`** — new stdlib-only MCP capability smoke probe. Remote MCP gets a HEAD-then-GET reachability check with HTTP-status-as-alive semantics (401/403/405 prove the server answered). Local MCP spawns the launcher for a 3-second window; missing launcher → `skip` (fresh-checkout safety), non-zero exit inside the window → `fail`, otherwise `alive`. `--json` mode for automation.
- **`scripts/collect_diagnostics.sh`** — timestamped local diagnostic bundle under `diagnostics/` (now git-ignored) collecting git metadata, validator log, dependency-pin report, flow / fullrepo / MCP-smoke state, runtime fingerprint, and optionally LSP + opencode doctor with `--include-doctor`.
- **`scripts/validate_instruction_docs.py`** — verifies `AGENTS.md` and `.claude/CLAUDE.md` exist, exceed a minimum-byte threshold, and contain required anchor headings. Catches accidental deletion / truncation / template-only state during a release.
- **`docs/observability.md`** — operational guide enumerating what to check first, the three plugin observability channels (toast / app log / tool metadata), the diagnostic-bundle contract, CI observability surface, and a failure-triage order.
- **`pyrightconfig.json`** — Python static type-check baseline for the `scripts/` tree. `typeCheckingMode: basic`, missing-type-stubs noise suppressed.
- **`.github/workflows/dependency-check.yml`** — weekly cron (Mon 06:00 UTC) + `workflow_dispatch` that runs `scripts/check_deps_freshness.sh --json` and surfaces the pinned-dependency JSON envelope via `GITHUB_STEP_SUMMARY`. SHA-pinned actions; least-privilege `contents: read` permissions.

### Changed

- **CRITICAL — `.opencode/plugins/ry-tool-hints.ts` MCP tool ID format**. The `tool.definition` hook receives `input.toolID` as `sanitize(serverName) + "_" + sanitize(toolName)` (single underscore; dashes preserved). The previous HINTS map used the Claude-Code-style `mcp__server__tool` prefix, so none of the 14 advertised routing hints fired — they were silently dead code. Rewrite every key to the correct form (`serena_find_symbol`, `chrome-devtools_list_console_messages`, `context7_resolve-library-id`, `sequential-thinking_sequentialthinking`, …). Source: `packages/opencode/src/mcp/index.ts` in `sst/opencode` v1.14.48.
- **All 7 plugins emit advice via `client.app.log` + `client.tui.showToast`** instead of `console.log`. `console.log` reached only the server log file and was invisible to the user. Toasts now surface git-push reminders, destructive-rm warnings, force-push blocks, env-protection rationales, conventional-commit advice, post-commit `/ry-sync` nudges, and session-idle reminders. Notify calls are best-effort (try/catch silent fallback) so a client-side hiccup cannot block tool execution.
- **`opencode.json` `agent.title` and `agent.summary` pinned to `claude-haiku-4-5-20251001`** at `temperature: 0.2`. These two hidden built-in agents previously inherited the global Sonnet 4.6 budget; switching to Haiku saves ~80% on their per-session cost (title gen ~200 tokens, summary ~1k tokens) with no quality impact for short summarisation tasks.
- **`opencode.json` `agent.compaction` pinned to `claude-sonnet-4-6`** at `temperature: 0.2`. Compaction is correctness-critical (the next turn sees the compressed context) — keep Sonnet quality, lock low temperature to suppress drift.
- **`opencode.json` `compaction` config tuned** with `tail_turns: 12`, `preserve_recent_tokens: 8000`, `reserved: 4000`. `tail_turns` preserves the most-recent plan→build→review cycle uncompressed; `preserve_recent_tokens` protects the freshest technical context; `reserved` leaves headroom for the next response. Documented in OpenCode v2 SDK types `dist/v2/gen/types.gen.d.ts:925-933`.
- **Reviewer subagents explicit `task: ask` + `external_directory: deny`** added to `flow-architecture-review`, `flow-consistency-review`, `flow-integration-review`, `flow-quality-review`, `flow-security-review`, `flow-verification-review`. `flow-memory-sync` and `ry-explore` use the stricter `task: deny`. Defense in depth for OpenCode v1.14.31 and v1.14.46 subagent permission-inheritance fixes — without explicit values the inheritance fix landed only when parents specified them.
- **6 slash commands gain bilingual descriptions** (`ry-deploy`, `ry-init`, `ry-newp`, `ry-review`, `ry-start`, `ry-sync`) matching the Russian-leading + English-trailing convention used across all 32 skill descriptions.
- **4 ADRs in `docs/decisions/`** gain a top-of-file supersession banner warning that the legacy example model IDs (`claude-sonnet-4-20250514`, `claude-haiku-4-20250514`, `claude-opus-4-20250514`) shown in code blocks produce `ConfigInvalidError` on OpenCode v1.14.30+. ADR bodies preserved verbatim (MADR 4.0.0 immutability).
- **`.claude/CLAUDE.md` stale counts refreshed**: `opencode.json` 181→194 lines, pytest 184→194 cases / 4→6 suites, VERSION marker 0.9.0→0.9.1.
- **`scripts/detect_project_checks.sh` TypeScript typecheck fallback** swapped `npx tsc --noEmit` → `bunx tsc --noEmit`. AGENTS.md L213 bans `npx`; the script now follows its own policy.
- **`.github/workflows/validate.yml`** workflow-level `permissions: { contents: read }`. Closes the OSSF Scorecard Token-Permissions check; the validator only needs read access.
- **`AGENTS.md` `Plugins` block expanded** to 10 entries (was 8) and documents the new hook subscriptions, `client.tui.showToast` / `client.app.log` migration, and the OpenCode v1.14.48 tool-ID format note inside the `ry-tool-hints` row.
- **`AGENTS.md` `Validation Commands` block** lists the four new entries (`smoke_mcp_capabilities.py`, `validate_instruction_docs.py`, `collect_diagnostics.sh`, observability doc link) and the updated pytest count.
- **`README.md`** plugin count 8→10, catalog refreshed with `.claude/CLAUDE.md` row + observability doc + dependency-check workflow + 14 scripts, and a new "Project structure" tree block.
- **`.gitignore`** removes a duplicate `!.env.example` negation line and adds `diagnostics/` (output dir of `scripts/collect_diagnostics.sh`).

### Test coverage

- **194 pytest cases** in **6 suites** (unchanged numerically, but `test_opencode_resolve.py` hardened against pytest stdout-capture truncation: `test_debug_config_resolves_cleanly` now uses a head-substring probe instead of full `json.loads`; `test_debug_skill_count_matches_directory` anchors the regex to `^\s*"name":\s*"[a-z][\w-]*"` so prose hits inside descriptions cannot inflate the count; plugin-info test references the `EXPECTED_PLUGINS` tuple instead of hard-coding "eight").
- `test_plugin_surface.py` extended: HINTS regex now matches the OpenCode v1.14.48 `server_tool` format; `LEGACY_BANNED` now rejects the entire `mcp__` substring in the live HINTS map (legacy format remains allowed in module-header comments).

### Anti-patterns explicitly NOT ported from sibling marketplaces

This release rejects several Codex / Claude-Code idioms that do not belong in an OpenCode marketplace:

- `.codex-plugin/plugin.json` manifests, `hooks.json` shell-script registries, `${CLAUDE_PLUGIN_ROOT}` env indirection, `system/AGENTS.md` install templates, and `mcp__server__tool` Claude-Code-style tool IDs are all rejected at the validator or plugin level.
- The plugin-bundled directory layout `plugins/rldyour-*/` used by `rldyour-codex` and `rldyour-claudecode` is intentionally NOT replicated — OpenCode discovers agents, skills, commands, and plugins from flat `.opencode/{agents,skills,commands,plugins}/` paths.

## [0.9.1] - 2026-05-13

Hardening pass closing every defer item flagged by the 0.9.0 reviewer round, plus the previously-external decision to ship a real Claude Code project memory file.

### Added

- `.claude/CLAUDE.md` — Claude Code project memory written as a self-contained guide (not a thin pointer to AGENTS.md per `project-instructions-policy` anti-pattern). Tells a Claude-Code-resident developer that this repo is an OpenCode marketplace, where canonical knowledge lives, what NOT to do (treat OpenCode skills/agents/commands as Claude Code primitives), which validation gates apply, and how to reach AGENTS.md, references, decisions.
- `scripts/tests/test_plugin_surface.py` (6 cases) — defensive checks that catch regressions: plugin set on disk equals AGENTS.md count; `ry-tools` registers exactly the 5 advertised tool IDs; `ry-tool-hints` HINTS keys reference real `opencode.json.mcp` server keys; legacy `mcp__context7__get-library-docs` alias cannot be re-introduced; dead `project as { path? }` cast cannot reappear in any plugin.
- `scripts/tests/test_opencode_resolve.py` (4 cases, skipped when `opencode` CLI absent) — end-to-end integration: `opencode debug config` resolves cleanly; `opencode debug info` lists all 8 plugins; resolved skill count equals directory count; every `.opencode/agents/*.md` resolves under `opencode debug agent`. Catches schema-validation regressions that pass static checks but fail live OpenCode.
- Inline concurrency + sanitize-order notes in `ry-command-audit.ts` documenting the deliberate non-atomic read-modify-write (single Bun event loop serialises within process) and the deliberate sanitize-before-slice order (guarantees no credential reaches the log regardless of position).

### Changed

- `.github/workflows/validate.yml` — `actions/checkout@v4` and `actions/setup-python@v5` pinned to commit SHA (`34e114876b0b11c390a56381ad16ebd13914f8d5` and `a26af69be951a213d495a4c3e4e4022e16d87065` respectively). Defends CI against tag-hijack on the action repositories. Verified via `gh api repos/actions/<name>/git/refs/tags/<tag>`.

### Test coverage

- Total pytest cases: **194** (was 184). Breakdown: 27 validate_helpers + 12 extract_pins + 129 skill_routing + 16 command_audit_sanitizer + 6 plugin_surface + 4 opencode_resolve.

## [0.9.0] - 2026-05-13

OpenCode plugin-surface expansion. Adopt three previously-unused hook types so the marketplace exercises the full v1.14.48 plugin API instead of just session/tool/shell observation.

### Added

- **`.opencode/plugins/ry-tools.ts`** — 5 custom tools registered via the `tool` plugin hook so the LLM can drive diagnostic scripts directly:
  - `rldyour_validate_config` — runs `bash scripts/validate_config.sh`.
  - `rldyour_check_deps` — runs `bash scripts/check_deps_freshness.sh --json`.
  - `rldyour_lsp_health` — runs `bash scripts/check_lsps.sh`.
  - `rldyour_git_audit` — runs `bash scripts/git_sync_audit.sh`.
  - `rldyour_fullrepo_status` — runs `bash scripts/fullrepo_sync.sh status-json`.
  Each tool stamps `ctx.metadata({ title, metadata: { exitCode } })` so the TUI shows pass/fail at a glance.
- **`.opencode/plugins/ry-command-audit.ts`** — `command.execute.before` plugin appends one credential-sanitized line per slash command invocation to `.serena/.command_audit.log` (runtime marker; never committed; 256 KiB rolling cap with reset).
- **`.opencode/plugins/ry-tool-hints.ts`** — `tool.definition` plugin appends a one-sentence routing hint to known MCP tool descriptions (Serena `find_symbol`, Chrome DevTools console, Context7 docs, Semgrep scan, Sequential Thinking, etc.). Encodes the AGENTS.md tool-priority matrix inline to the LLM.
- **`scripts/tests/test_skill_routing.py`** — 129 parametrized pytest cases (32 skills × 4 routing checks + 1 uniqueness): description length 80-1024, presence of Russian routing phrase (`Используй для` / `Use for`), presence of English routing block (`EN triggers:` or English-leading head), skill name kebab-case. Borrowed from codex marketplace's deterministic-routing-policy pattern, adapted to OpenCode's description-based auto-routing.
- **`references/opencode-plugin-patterns.md`** — full reference for the `@opencode-ai/plugin` v1.14.48 hook surface (server-side + TUI), patterns adopted in this repo, explicit list of unused-but-known hooks, and CLI extension points the marketplace can drive (`opencode run / debug / serve / web / acp / github / pr / stats / export / import`).

### Changed

- Skill descriptions for `flow-post-task-sync`, `instruction-docs-sync`, `ry-deploy`, `ry-init`, `ry-newp`, `ry-review`, `ry-start` extended with explicit `Используй для:` (RU triggers) and `EN triggers:` (EN keyword block) so OpenCode auto-routing matches both languages reliably. Verified by the new `test_skill_routing.py` suite.
- AGENTS.md Plugins section now documents all 8 plugins with exact hook subscriptions and links to `references/opencode-plugin-patterns.md`.
- README catalog tables updated: 8 plugins (was 5), 16 reference docs (was 15), 3 pytest suites with 168 cases (was 1 with 27).

## [0.8.1] - 2026-05-13

Post-0.8.0 hardening based on parallel reviewer findings (architecture / quality / consistency / integration / verification / security tracks).

### Added

- `scripts/tests/test_validate_helpers.py` (27 cases) and `scripts/tests/test_extract_pins.py` (12 cases) — full pytest coverage of the validator and pin extractor. Run via `python3 -m pytest scripts/tests/` or `uvx --from "pytest==9.0.2" pytest scripts/tests/`.
- `scripts/tests/__init__.py` and `scripts/tests/conftest.py` — package marker and pytest session config (adds `scripts/` to `sys.path`). Removes the previous inline `sys.path.insert` hack from the test module body.
- `scripts/check_deps_freshness.sh` + `scripts/_extract_pins.py` — list every pinned MCP dependency in `opencode.json` (npm via bunx, PyPI via uvx, Dart SDK). `--json` mode emits a documented JSON envelope (`{pins: [{kind,server,name,version}], count}`).
- `DuplicateYamlKey` exception in `_validate_helpers.py` — rejects skill/agent/command frontmatter that contains the same top-level key twice (regex YAML parser previously kept the first match silently).
- `.github/workflows/validate.yml` — Python 3.13 setup + pinned `pytest==9.0.2` install + pytest run. CI and local validation now exercise the same surface.
- `docs/decisions/*.md` — architecture decision archive (4 files moved from former `thinking/` directory in commit `159fd99`).
- AGENTS.md Source Of Truth gains a `docs/decisions/*.md` entry; Validation Commands gains pytest, check_deps_freshness, and `opencode debug *` rows.
- README Validation block lists pytest + check_deps_freshness; Catalog has new rows for `docs/decisions/` and `scripts/tests/`.

### Changed

- `_validate_helpers.py`: `_yaml_top_key` now (a) supports YAML block scalars (`description: |`), (b) reads `utf-8-sig` so files with UTF-8 BOM parse correctly, (c) anchors trailing whitespace as `[^\S\n]*` so an empty inline scalar no longer captures the next line's text.
- `_validate_helpers.py`: SSoT command-block gate added — rejects an `opencode.json` that defines a `command` block (commands must live in `.opencode/commands/*.md`).
- `scripts/validate_config.sh`: rewritten without inline zsh-heredoc Python; delegates to `_validate_helpers.py`. Adds `log_warn` / `log_info` helpers consistent with other scripts.
- `scripts/fullrepo_sync.sh`: `AGENT_ONLY_PATTERNS` updated `thinking/` → `docs/` (matches actual layout after the `159fd99` rename). Secret detector warning now uses `cut -d: -f1` (was `cut -d: -1`, a no-op flag that suppressed the file path in the warning).
- `scripts/check_deps_freshness.sh`: `--json` path writes directly to stdout (no `mktemp` temp file, no trap risk).
- `scripts/_extract_pins.py`: `UV_FROM_RE` accepts PyPI names containing `.` (e.g. `zope.interface`); module docstring documents the full JSON envelope contract.
- AGENTS.md Plugins section rewritten against `.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts` v1.14.48: removed non-existent `permission.asked`/`permission.replied`/`tui.*` server hooks; added `config`, `chat.message`, `chat.params`, `chat.headers`, `command.execute.before`, `tool.definition`, `auth`, `provider`, four `experimental.*`.
- `.opencode/plugins/ry-bootstrap.ts`: MCP list pushed into compaction context is read dynamically from `opencode.json` via `Bun.file()` instead of being hardcoded. Catch path logs a warning before falling back to neutral hint.
- `.opencode/plugins/ry-sync-reminder.ts`: removed duplicate `tool.execute.after` handler — Conventional Commits advice owned exclusively by `ry-flow-hooks.ts`.
- `.opencode/agents/customize-opencode.md`: body forbids adding `command` block to `opencode.json`; color schema constraint documented; new-agent flow uses `opencode debug agent <name>`.
- `.github/workflows/validate.yml`: CI delegates to `bash scripts/validate_config.sh` instead of inline Python/bash checks (eliminates CI-vs-local schema drift).
- README placeholder env vars renamed `your-key` → `YOUR_PLACEHOLDER_KEY` so the `fullrepo_sync.sh publish` secret detector whitelist correctly ignores them.

### Removed

- `.claude/CLAUDE.md`: Claude Code project-memory thin pointer (anti-pattern called out by `project-instructions-policy` skill; AGENTS.md cross-tool standard covers Claude Code without a separate memory file).

### Fixed

- Model IDs in `opencode.json` and `.opencode/agents/*.md` migrated to OpenCode v1.14.48 registry-valid IDs (`claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-opus-4-7`). Previous IDs caused `config.providers` / `provider.list` / `app.agents` / `config.get` `ConfigInvalidError`.
- Agent `color` frontmatter migrated from named CSS colors to hex / enum per schema. Prior values (`blue`, `yellow`, `purple`, …) were rejected by OpenCode v1.14.
- `_validate_helpers.py` correctly handles `description: |` block scalars and UTF-8 BOM; empty inline `description:` no longer silently slurps the next line.

## [0.8.0] - 2026-05-13

Validated against OpenCode v1.14.48 (`opencode debug config` resolves cleanly).

### Added

- **`docs/`**: marketplace operator guides — `release-process.md`, `dependency-updates.md`, `rollback-restore.md`.
- **`scripts/_validate_helpers.py`**: Python module backing the rewritten `scripts/validate_config.sh`. Validates `opencode.json` shape, skill name/description, agent frontmatter (description + mode + color enum or hex), command frontmatter, VERSION semver. Supports YAML block scalars (`description: |`) and UTF-8 BOM. Single source of truth gate: rejects `command` block in `opencode.json` (commands must live in `.opencode/commands/*.md`).
- AGENTS.md skill spec: explicit allowed optional frontmatter (`license`, `compatibility`, `metadata`) and explicit forbidden Claude-Code/Codex residue fields.
- AGENTS.md plugin event list expanded to match OpenCode v1.14 actual surface.
- AGENTS.md agent spec: explicit `color` schema constraint (hex `^#[0-9a-fA-F]{6}$` or enum `primary|secondary|accent|success|warning|error|info`).
- README catalog tables for Models, MCP servers, reviewer subagents (with schema-valid colors), validation commands.

### Changed

- **`.opencode/plugins/ry-bootstrap.ts`**: MCP list pushed into compaction context is now read dynamically from `opencode.json` via `Bun.file()` instead of being hardcoded. Catch path now logs a warning before falling back.
- **`.opencode/plugins/ry-sync-reminder.ts`**: removed duplicate `tool.execute.after` handler — Conventional Commits advice is owned exclusively by `ry-flow-hooks.ts`.
- **`.opencode/agents/customize-opencode.md`**: body forbids adding `command` block to `opencode.json` (single source of truth); color schema constraint documented; new-agent flow uses `opencode debug agent <name>` for verification.
- **`.github/workflows/validate.yml`**: CI now delegates to `bash scripts/validate_config.sh` instead of inline Python/bash checks, keeping CI and local validators identical.
- **`scripts/validate_config.sh`**: rewritten without zsh-heredoc Python (delegates to `_validate_helpers.py`). Added `log_warn` / `log_info` helpers consistent with other scripts.
- `docs/dependency-updates.md`: removed dangling "track via TODO in CHANGELOG" cross-reference.

### Removed

- **`.claude/CLAUDE.md`**: Claude Code project-memory pointer file. This is an OpenCode-native marketplace and the AGENTS.md cross-tool standard (https://agents.md/) already covers any Claude Code use case. The previous thin-pointer file matched the anti-pattern called out in `project-instructions-policy` skill.

### Fixed

- Model IDs in `opencode.json` and all `.opencode/agents/*.md` use OpenCode v1.14.48 registry-valid identifiers (`claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-opus-4-7`). Prior IDs (`claude-sonnet-4-20250514`, `claude-haiku-4-20250514`, `claude-opus-4-20250514`) caused `config.providers` / `provider.list` / `app.agents` / `config.get` `ConfigInvalidError`.
- Agent `color` frontmatter migrated from named CSS colors to hex / enum per schema. Prior values (`blue`, `yellow`, `purple`, `orange`, `green`, `red`, `pink`, `cyan`) were rejected by OpenCode v1.14 (only hex `^#[0-9a-fA-F]{6}$` or enum `primary|secondary|accent|success|warning|error|info` accepted).
- `_validate_helpers.py` handles `description: |` block scalars correctly; previously returned the literal `|` and skipped the length check.
- `_validate_helpers.py` uses `utf-8-sig` encoding so files with UTF-8 BOM do not produce spurious `missing frontmatter delimiter` errors.

## [0.7.0] - 2026-05-12

### Added

- **4 missing commands**: ry-design, ry-explore, ry-sec-review, ry-rules-review (matching reference implementations).
- **LSP utility scripts**: check_lsps.sh (health check for 17+ language servers) and install_lsps.sh (brew-first installation).
- **Flow utility scripts**: flow_post_task_state.sh (JSON state computation), git_sync_audit.sh, deploy_readiness.sh, detect_project_checks.sh.
- **New plugin**: ry-flow-hooks.ts (post-tool commit advice and auto-sync nudge).
- AGENTS.md updated with validation commands section listing all 9 scripts.

### Changed

- Commands now use OpenCode-specific features: `subtask: true` for ry-explore, correct MCP tool names (`mcp__figma__*` not `mcp__plugin_rldyour-mcps_figma__*`).
- All 10 commands now present (6 original + 4 new), matching reference implementation coverage.

## [0.6.0] - 2026-05-12

### Added

- **Fullrepo sync script** (`scripts/fullrepo_sync.sh`): bootstrap-init, restore, publish, status, status-json — full agent-only file branch management.
- `.env.example` documenting required environment variables (CONTEXT7_API_KEY, GITHUB_PERSONAL_ACCESS_TOKEN).
- Domain boundaries section in AGENTS.md mapping each skill/agent/command to its owning domain.
- Don'ts section in AGENTS.md with 10 explicit prohibitions.
- Validation commands section in AGENTS.md documenting all scripts.
- `.git/info/exclude` pattern management documented in Git and Sync section.
- Updated MCP servers table: dart-flutter now enabled, figma URL corrected to `/mcp`.

### Changed

- **Single source of truth for agents and commands**: removed all subagent and command definitions from `opencode.json` — they live exclusively in `.opencode/agents/*.md` and `.opencode/commands/*.md`.
- **MCP timeouts reduced**: 30s for local servers, 15s for remote (was 90s/60s).
- **AGENTS.md major rewrite**: added domain boundaries, don'ts, validation commands, fullrepo sync docs, plugin event reference.
- **Plugins enhanced**: ry-bootstrap.ts now includes MCP server list and reviewer subagent list in compaction context; ry-env-protection.ts has improved pattern matching with .env.example whitelist; ry-shell-strategy.ts adds --force-with-lease guard and destructive rm warning; ry-sync-reminder.ts adds conventional commit format advice on commit events.

## [0.5.0] - 2026-05-12

### Changed

- **Breaking: single source of truth for agents and commands.**
  - Removed 8 subagent definitions from `opencode.json` — they live only in `.opencode/agents/*.md`.
  - Removed 6 command definitions from `opencode.json` — they live only in `.opencode/commands/*.md`.
  - `opencode.json` now only contains `build` and `plan` primary agent overrides (permissions).
- Reduced MCP timeout values: 30s for local servers, 15s for remote (was 90s/60s).
- Updated AGENTS.md to document single-source-of-truth convention explicitly.

## [0.4.0] - 2026-05-12

### Changed

- LSP configuration changed from `"lsp": true` to `"lsp": {}` (object = built-ins enabled + custom overrides).
- Added 8 custom LSP servers to cover all languages from reference implementations:
  - `ruff` (Python linter companion to pyright)
  - `vscode-html` (HTML)
  - `vscode-css` (CSS/SCSS/SASS/Less)
  - `vscode-json` (JSON/JSONC)
  - `docker` (Dockerfile)
  - `taplo` (TOML)
  - `marksman` (Markdown)
  - `qmlls` (Qt QML, optional)
- Total LSP coverage: 35+ built-in + 8 custom = 43+ language servers.
- AGENTS.md LSP section expanded with runtime rules and custom server table.

## [0.3.0] - 2026-05-12

### Changed

- MCP configuration: complete rewrite from scratch based on both reference implementations.
- Replaced `npx -y` with `bunx` for all npm-based MCP servers (serena, sequential-thinking, playwright, chrome-devtools, context7, shadcn).
- Fixed serena: changed from `@anthropic/serena-mcp` to `serena-agent==1.3.0` via `uvx` with correct flags.
- Fixed sequential-thinking: version `0.7.0` → `2025.12.18`, added `DISABLE_THOUGHT_LOGGING` env var.
- Fixed playwright: added `--headless` and `--caps=network,storage,testing,devtools` flags.
- Fixed figma URL: `/` → `/mcp`.
- Added `timeout` values: 90000ms for local servers, 60000ms for remote servers.
- Added 5 missing MCP servers: chrome-devtools, semgrep, shadcn, dart-flutter, openai-docs.
- Total MCP servers: 13 (8 local, 5 remote; dart-flutter disabled by default).

## [0.2.0] - 2026-05-12

### Added

- OpenCode plugin system with 4 event-driven plugins replacing advisory lifecycle hooks.
- `ry-bootstrap.ts`: session.created context injection and compaction context preservation.
- `ry-env-protection.ts`: tool.execute.before read/bash blocking for sensitive file paths.
- `ry-shell-strategy.ts`: shell.env non-interactive git env injection and pre-push advisory.
- `ry-sync-reminder.ts`: session.idle reminder to run /ry-sync before ending session.
- `.opencode/package.json` for plugin TypeScript dependencies.
- `opencode.json` plugin section (empty array for future npm plugins).
- AGENTS.md updated with Plugins section documenting events, structure, and rldyour plugins.

## [0.1.0] - 2026-05-12

### Added

- Initial rldyour-opencode marketplace with full OpenCode configuration.
- `opencode.json` master config with providers, MCP servers, LSP, agents, permissions, commands.
- 9 subagent definitions for review, memory sync, and deep research workflows.
- 32 skill definitions covering flow, Serena, rules, explore, browser, design, security, and LSP domains.
- 6 slash commands for SDLC workflow (ry-init, ry-start, ry-review, ry-newp, ry-deploy, ry-sync).
- 16 reference documents for skills and agents.
- Bootstrap, validation, and diagnostics scripts.
- AGENTS.md cross-tool root instructions adapted for OpenCode format.
- Serena project configuration and initial memory structure.
- 7 MCP servers configured (serena, sequential-thinking, playwright, context7, deepwiki, grep, github, figma).
- Built-in LSP support enabled for 30+ languages.
- Reviewer subagents with per-agent permissions (read-only, bash allowlisted for git commands).
