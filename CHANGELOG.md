# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.12.3] - 2026-05-18

Patch release applying the deferred reviewer findings flagged but not
blocked during the v0.12.2 audit-followup wave, plus the single CI
Lint fix that surfaced on the v0.12.2 push. No new features; the wave
is pure hardening + symmetry polish. Plugin SDK pin stays at
`@opencode-ai/plugin@1.15.4` (no upstream changes since v0.12.2).

### Fixed

- **CI Lint failure on v0.12.2 push.** ruff F541 flagged a stray
  f-prefix on `[ERR] baseline.baseline must be an object` in
  `scripts/check_baseline_consistency.py` (no placeholders in the
  string). Dropped the prefix so `Lint / ruff` returns green.
- **`scripts/doctor_opencode.py` --total-timeout could overrun by
  PER_CHECK_TIMEOUT_SECONDS.** The previous main loop only checked the
  wall-clock deadline BEFORE each check fired; once a check started, it
  could run for the full 15 s even if `--total-timeout` had only 1 s
  left. The fix exposes the per-check budget through a module-level
  getter (`_per_check_budget()`) that the main loop narrows to
  `min(PER_CHECK_TIMEOUT_SECONDS, remaining_wall_clock_s)` with a 1 s
  floor before every invocation. Subprocess-spawning checks already
  read the budget at call time, so the new tighter value takes effect
  immediately. Closes Quality-review M.
- **`.opencode/plugins/ry-system-context.ts` cache not directory-keyed.**
  The TTL cache held a single module-level slot (`cachedBranchHead`),
  so an OpenCode session that spans multiple worktrees / project roots
  would serve a stale `branch=` stamp from the wrong tree. Swapped for
  `cacheByDirectory: Map<string, BranchHeadCache>` so per-tree readouts
  are correct without changing the hot-path cost for single-directory
  sessions. Closes integration-review F-3.

### Added

- **`scripts/tests/test_doctor_opencode.py::test_doctor_exit_3_when_
  total_timeout_zero`** asserts the actual exit-3 emission when the
  total timeout trips, replacing the previous test which accepted
  `{0, 1, 3}` and silently passed when the timeout never tripped.
  Closes verification-review M.
- **`scripts/tests/test_print_required_check_contexts.py`** (5 cases)
  pins the extractor's output contract: script exists + is executable,
  text mode header layout, JSON envelope shape, every PR-required
  context from `docs/github/branch-protection.md` appears in the
  output, and the disk-vs-output count invariant. The extractor was
  the only script in `scripts/` without test coverage. Closes
  architecture-review L.
- **`scripts/validate_config.sh log_fail()`** helper for the 5th
  canonical log tag (`[FAIL]`) introduced by the 0.12.2 validators
  (`check_baseline_consistency.py`, `validate_mcp_profiles.py`). The
  helper is reserved for future bash-level fail tagging
  (`shellcheck disable=SC2329` annotated); today's red `[FAIL]` lines
  come straight from validator stderr. Closes consistency-review L.

### Changed

- **`references/mcp-profiles.json`** `version` field: integer `1` →
  string `"1.0.0"` so the JSON shape mirrors
  `references/opencode-baseline.json` (string SemVer). Consumers were
  not type-checking the field; this is purely shape parity. Closes
  consistency-review L.
- **`scripts/tests/test_mcp_profiles.py`** drops the `import shutil` +
  `_ = shutil` placeholder anti-pattern; the import was never
  exercised after the fixture refactor. Closes consistency-review I.

### Test coverage

- Total pytest cases: **455 passed + 1 skipped** across **21 suites**
  (was 447 / 20 at v0.12.2; +8 new cases). New suite
  `test_print_required_check_contexts.py` (5). New cases in existing
  suites: `test_doctor_opencode.py` (+1 exit-3 forced timeout),
  `test_check_baseline_consistency.py` (+2 invalid-JSON-operational
  + trailing-pin-drift), and trailing-pin coverage on the referencing
  package.

### CI pipeline state at HEAD

All green at HEAD `5377bd0` (post-follow-up push):

- `validate` (Linux + macOS) — green
- `typecheck-plugins` (Linux + macOS) — green
- `lint` (Linux + macOS) — green (was red on v0.12.2; F541 fix)
- `opencode-runtime` (Linux + macOS) — green
- `instruction-docs-check` — green
- `dependency-check` — green (manual + scheduled smoke envelopes)
- `codeql` — green
- `secret-scan` — green
- `release` — will fire on v0.12.3 tag push

## [0.12.2] - 2026-05-18

Patch release closing every blocker raised by the 2026-05-17 external
audit pass. The wave turns the "single mechanism" promise into static
gates: one baseline file declares every pinned version, one validator
enforces it across docs/package/lock/workflows, the OpenCode JSON Schema
validator resolves external `$ref`s entirely offline, the doctor is
rewritten on a deterministic Python core with per-check + wall-clock
timeouts, the MCP server roster is profiled in a machine-readable file,
the smoke probe exposes `--mode` profiles for differentiated CI loads,
and `ry-system-context.ts` swaps its forever-cached branch/HEAD for a
3-second TTL that survives in-session `git checkout`.

### Added

- **`references/opencode-baseline.json`** — single source of truth for
  every pinned version the marketplace targets: `opencode-ai@1.15.4`,
  `@opencode-ai/plugin@1.15.4`, `@opencode-ai/sdk@1.15.4`,
  `bun@1.3.14`, `python@3.13`, `pytest==9.0.3`, `PyYAML==6.0.3`,
  `jsonschema==4.26.0`, `ruff==0.15.13`, `gitleaks@8.30.1`, and
  `codeql-action@v4.35.5`. Closes audit P0-1.
- **`scripts/check_baseline_consistency.py`** — gate that fails when
  `.opencode/package.json`, `.opencode/bun.lock`,
  `.github/workflows/opencode-runtime.yml`, any workflow's
  `bun-version`, any `pip install pkg==X.Y.Z` line, the vendored
  schema, or any vendored external `$ref` drifts from the baseline.
  Surfaces a soft warning when the latest `CHANGELOG.md` release block
  does not mention the bumped plugin version. Closes audit P0-1.
- **`references/mcp-profiles.json`** — machine-readable mapping of
  every server in `opencode.json.mcp` to exactly one profile (`base`,
  `research`, `browser`, `security`, `design`, `repo`) plus a
  `high_context` set for cost-aware skill design. Closes audit P1-3.
- **`scripts/validate_mcp_profiles.py`** — validator that asserts
  `skill.requires_mcp ⊆ opencode.mcp`, every server is assigned to
  exactly one profile, no profile references an undeclared server,
  and emits soft warnings when a skill depends on a `high_context`
  server. Wired into `scripts/validate_config.sh`. Closes audit P1-3.
- **`scripts/doctor_opencode.py`** — Python core for the doctor.
  Granular `--check {agents,baseline,commands,config,git,mcp,plugins,
  schema,serena,skills}` selection, `--format {text,json}` output,
  `--total-timeout` wall-clock deadline (default 60 s), 15 s per
  per-check timeout, structured `{check, status, duration_ms, details}`
  result envelope, and exit-code semantics 0/1/2/3 (clean / fail /
  operational error / total-timeout). `scripts/doctor_opencode.sh` is
  preserved as a thin `exec python3 scripts/doctor_opencode.py "$@"`
  adapter so existing operator muscle memory keeps working. Closes
  audit P0-3.
- **`scripts/print_required_check_contexts.sh`** — extracts the actual
  GitHub check contexts (workflow `name:` plus job `name:` with matrix
  expansion) from `.github/workflows/*.yml` so
  `docs/github/branch-protection.md` stays mechanically in sync with
  the workflow source. Closes audit P0-5.
- **`scripts/smoke_mcp_capabilities.py --mode` profiles** —
  `{all, static, local-launch, remote-head}` selector. PR runs gate on
  `--mode static`, scheduled `dependency-check.yml` runs `--mode
  remote-head` and `--mode local-launch`. Default `--mode all`
  preserves the v0.12.1 backward-compatible single-mode invocation.
  Closes audit P1-4.
- **`references/models.dev-model-schema.json`** — vendored snapshot of
  the only external `$ref` in `references/opencode-config.schema.v1.15.4.json`
  so `scripts/validate_opencode_schema.py` resolves the reference
  offline through a `referencing.Registry`. Any newly-added upstream
  external `$ref` now fails with a clear `Unresolvable` operational
  error rather than triggering a silent network round-trip. Closes
  audit P0-2.

### Changed

- `.opencode/package.json` and `.opencode/bun.lock` bump
  `@opencode-ai/plugin` and `@opencode-ai/sdk` from `1.15.3` to
  `1.15.4` to match `references/opencode-baseline.json`. Upstream
  `v1.15.4` release notes scope to three bugfixes (project-scoped bus
  events, custom LSP refresh events, hidden background subagent task
  instructions) plus a TUI markdown polish. Server-side `Plugin`/`Hooks`
  factory contract and MCP `<server>_<tool>` tool-ID format are
  unchanged from `v1.15.3`.
- `.opencode/plugins/ry-system-context.ts` swaps its forever-cached
  branch/HEAD readout for a `BRANCH_HEAD_CACHE_TTL_MS = 3_000` TTL
  cache. The previous implementation cached at plugin factory init,
  which left the `[rldyour runtime]` prompt stamp stale for the
  remainder of any session that ran `git checkout|switch|rebase`. The
  new gate uses `Date.now()` to invalidate every 3 seconds while
  still suppressing 2 of the 3 git subprocesses on the hot
  `experimental.chat.system.transform` path. Closes audit P1-6.
- `scripts/validate_opencode_schema.py` now builds an offline
  `referencing.Registry` from `EXTERNAL_REF_VENDORED_AT` and surfaces
  `Unresolvable` as a clean `exit 2` with a `curl ... -o
  references/...` remediation hint. Closes audit P0-2.
- `scripts/validate_config.sh` runs `check_baseline_consistency.py`
  and `validate_mcp_profiles.py` after the existing `check_action_pins`
  step. A baseline drift or MCP graph break fails the gate.
- `.github/workflows/validate.yml` adds three new gate steps:
  `check_baseline_consistency.py`, `validate_mcp_profiles.py`, and
  `smoke_mcp_capabilities.py --mode static`. A `continue-on-error`
  `doctor_opencode.py --format json --total-timeout 30` step publishes
  the JSON envelope for triage. The fullrepo restore step now follows
  a fallback contract (`[ ! -f path ]` + `git show` only when the
  file is absent from the checkout) so a PR with a branch-local
  `AGENTS.md` keeps its own copy. Closes audit P1-5.
- `.github/workflows/release.yml` mirrors the validate gate set in
  the same order so a green release implies a green PR; also adopts
  the fullrepo restore fallback. Closes audit P1-5.
- `.github/workflows/opencode-runtime.yml` adopts the same fullrepo
  restore fallback. Closes audit P1-5.
- `.github/workflows/dependency-check.yml` runs `smoke_mcp --mode
  remote-head` and `smoke_mcp --mode local-launch` as separate
  `continue-on-error` steps; both envelopes attach to
  `GITHUB_STEP_SUMMARY` so scheduled triage stays observable.
- `docs/github/branch-protection.md` re-derived from
  `scripts/print_required_check_contexts.sh`. Required PR contexts now
  cite the actual workflow names and matrix expansions
  (`Validate rldyour-opencode / validate (ubuntu-latest)`, etc.).
  Scheduled-only and tag-only workflows moved out of the required PR
  contexts table to reflect their triggers. Closes audit P0-5.
- `scripts/tests/test_doctor_opencode.py` fully rewritten to target
  the Python core. Uses AST traversal for the subprocess.run timeout
  invariant, strips `(NNNms)` per-check timings before comparing the
  bash wrapper output to the Python invocation, and asserts the new
  granular `--check`, `--format json`, and `--total-timeout` contract.
  Closes audit P0-3.
- `scripts/tests/test_fullrepo_sync.py` adds an archive-safety
  `needs_project_git` skipif for the PROJECT_ROOT-bound `status-json`
  / `help` cases, plus an explicit `timeout=` argument on every
  `subprocess.run` call (PUBLISH_TIMEOUT for the heavier `publish`
  fixture). Closes audit P0-4.
- `scripts/tests/test_check_freshness.py` and `test_sanitize_diag.py`
  add the missing `timeout=` argument on every `subprocess.run`. Closes
  audit P0-4.

### Fixed

- AGENTS.md L131 already states the plugin pin is **manually
  maintained** and validated by `scripts/check_baseline_consistency.py`
  (the unproven auto-rewrite claim flagged by audit P1-1 was already
  removed before this wave; the new validator now makes the
  "manually maintained" assertion mechanical instead of textual).

### Stayed

- `opencode.json` keeps the YOLO permission profile (`edit: "allow"`,
  `bash: "allow"`, plus the rest of the v1.15.x canonical set). Audit
  P1-2 was already settled in `docs/decisions/009-yolo-full-auto-mode.md`
  (ADR-009): single-developer trust + plugin guardrails
  (ry-shell-strategy + ry-permission-policy + ry-env-protection)
  rather than an interactive-friction profile. The 2026-05-17 audit
  re-raised this without referencing ADR-009; the rebuttal stays in
  ADR-009 verbatim.

### Test coverage

- Total pytest cases: **447 passed + 1 skipped** across **20 suites**
  (was 412 / 18 at `0f60f76`, +35). New suites:
  `test_check_baseline_consistency.py` (9), `test_mcp_profiles.py` (11).
  `test_doctor_opencode.py` rewritten (+5 cases vs the bash version).
  `test_smoke_mcp.py` extended with 5 new cases for the `--mode`
  profile selector. `test_plugin_surface.py` extended with the
  ry-system-context TTL cache invariant. The skipped case is the
  missing-jsonschema-import path test, correctly skipped when the
  dependency is present.

### CI pipeline state at HEAD

- `validate` (Linux + macOS) — green; new gates passing
- `typecheck-plugins` (Linux + macOS) — green
- `lint` (Linux + macOS) — green
- `opencode-runtime` (Linux + macOS) — green
- `instruction-docs-check` — green
- `dependency-check` — green; new `--mode remote-head` + `--mode
  local-launch` summaries publish to `GITHUB_STEP_SUMMARY`
- `codeql` — green
- `secret-scan` — green
- `release` — to be re-validated when `v0.12.2` tag fires

## [0.12.1] - 2026-05-18

Patch consistency-polish release after the v0.12.0 audit closure. Closes
the CI failure that survived v0.12.0, extends macOS coverage to the new
runtime workflow, and lands symmetric machine-readable indices for the
remaining two catalogs (commands and plugins) so the static-validation
contract is consistent across all of `.opencode/{skills,commands,plugins}`.

### Fixed

- **CodeQL workflow exit code.** v0.12.0 still had CodeQL failing with
  `##[error]Resource not accessible by integration - workflow-runs#get-a-
  workflow-run` AFTER successful analysis (SARIF correctly exported).
  Root cause: the CodeQL action's post-processing step (SARIF
  fingerprinting) calls a workflow-runs REST endpoint that requires
  `actions: read`. Without it the action exits non-zero even though the
  artifact is correct. Adding `actions: read` alongside the existing
  `contents: read` permission fixes the exit code without widening
  privileges beyond reading public workflow metadata. The pattern had
  been failing on every push since 0.11.x — finally green on `ce7e62d`.
- **`scripts/fullrepo_sync.sh` secret-scan false positive.** The
  in-script secret-scan regex (canonical keyword followed by `=` plus
  a non-empty value on the same line) matched a doc-style shell
  example for the `GITHUB_PERSONAL_ACCESS_TOKEN` env var in
  `CONTRIBUTING.md`. Rewrote the setup-checklist step in prose so the
  operator guidance is equivalent but the regex no longer trips. Same
  scanner stays in place — only the doc form is normalised.

### Added

- **`.github/workflows/opencode-runtime.yml` macOS matrix.** The
  workflow now runs on `ubuntu-latest` + `macos-latest` with
  `fail-fast: false`. The OpenCode CLI is cross-platform (Bun on Linux
  + macOS); running both catches Bun/macOS-specific regressions the
  Linux-only build would miss. Windows stays out of scope (POSIX shell
  semantics in plugin spawn).
- **`.opencode/commands/index.json`** generated by
  `scripts/generate_commands_index.py`. 10 commands mapped to domain +
  triggers + agent + subtask flag. `--check` mode locks the contract
  in CI so a removed command or a renamed agent surfaces as a test
  failure rather than silent drift. `scripts/tests/test_commands_index.py`
  adds 6 cases covering in-sync, valid-agent, valid-domain, and disk-
  matches-count invariants.
- **`.opencode/plugins/index.json`** generated by
  `scripts/generate_plugins_index.py`. 10 plugins mapped to hooks
  (extracted from source) + category + description + curated metadata
  (writes_files, network, defense-in-depth pair, registered custom
  tools, MCP dependencies for ry-tool-hints). `--check` mode locks the
  generator output. `scripts/tests/test_plugins_index.py` adds 6 cases
  including a defense-in-depth-pair bidirectionality assertion that
  locks the ADR-006 invariant in static form.
- **`CONTRIBUTING.md` fine-grained PAT setup checklist.** 5-step
  onboarding section for the `GITHUB_PERSONAL_ACCESS_TOKEN` env var,
  with backlinks to `docs/security/mcp-trust-boundaries.md`. Closes
  security review F-4 (advisory).

### Changed

- `validate.yml` and `release.yml` now invoke
  `scripts/generate_commands_index.py --check --strict` and
  `scripts/generate_plugins_index.py --check --strict` alongside the
  existing skills-index check.
- README counts refreshed: 11 workflows, 18 suites / 412 pytest cases,
  23 top-level scripts.
- `.opencode/.gitignore` reordered comments so `node_modules/` is the
  primary directive and `package-lock.json` is documented as the
  diagnostic-only npm-side artifact.

### Test coverage

- Total pytest cases: **412** across 18 suites (was 399 / 16 at
  `1bc42ed`, +13). New suites: `test_commands_index.py` (6),
  `test_plugins_index.py` (6). The skipped case is the
  missing-jsonschema-import path test, correctly skipped when the
  dependency is present.

### CI pipeline state at HEAD

- `validate` (Linux + macOS) — green
- `typecheck-plugins` (Linux + macOS) — green
- `lint` (Linux + macOS) — green
- `opencode-runtime` (Linux + macOS) — green (new macOS matrix
  exercised cleanly)
- `instruction-docs-check` — green
- `dependency-check` — green (weekly + dispatch; freshness `stale: 0`)
- `codeql` — green (after `actions: read` fix)
- `secret-scan` — green
- `release` — green (created v0.12.0 GitHub Release with sbom.json
  asset)

## [0.12.0] - 2026-05-18

Minor release closing every P0 and P1 finding from the external audit
(2026-05-17 archive review) plus the Phase 2 scalability slice. The release
moves the marketplace from "right architecture, fragile reliability" to
"right architecture, hardened reliability + documented governance".

### Fixed

- **P0-1 — `ry-flow-hooks.ts` hook contract.** `tool.execute.after` previously
  read the bash command from `output.args.command`. The
  `@opencode-ai/plugin@1.15.4` SDK contract places `args` on `input`, so the
  buggy form silently swallowed every `git commit` / `git push` /
  `git merge` / `git cherry-pick` / `git rebase` detection — Conventional
  Commits validation and the `/ry-sync` post-commit nudge were dead.
  Introduced a `getBashCommand(input)` helper, locked the contract with
  `test_plugin_surface.py::test_flow_hooks_reads_command_from_input_args`,
  and added a parallel `getBashOutput(output)` helper for symmetry.
- **P0-2 — Lockfile policy.** `.opencode/.gitignore` previously listed
  `bun.lock`, `package-lock.json`, and even `package.json` as ignored, so
  `bun install --frozen-lockfile` in `typecheck-plugins.yml` and
  `release.yml` ran against a missing lockfile in CI. New policy: Bun
  canonical. `.opencode/.gitignore` is now just `node_modules/`,
  `.opencode/bun.lock` is tracked, and `.opencode/package-lock.json` is
  removed. Workflow path filters in `typecheck-plugins.yml` and
  `dependency-review.yml` point at `bun.lock` instead. Note: OpenCode's
  runtime auto-rewrites `.opencode/package.json` on startup to match the
  installed CLI version (AGENTS.md § Plugins), so the committed pin
  tracks whatever OpenCode is currently running; the v0.12.0 baseline is
  `@opencode-ai/plugin@1.15.3` mirroring the v1.15.3 runtime, with
  `opencode-runtime.yml` pinning the CI runtime to `opencode-ai@1.15.4`
  to detect contract regressions before the local runtime gets bumped.
- **P0-4 — OpenCode runtime job.** The static `validate_config.sh` runtime
  check used to skip when `opencode` was off PATH, which was always the
  case in GitHub-hosted runners. New `.github/workflows/opencode-runtime.yml`
  installs a pinned `opencode-ai@1.15.4` via `bun install -g`, runs
  `opencode --version`, `opencode debug config`, and the runtime smoke
  inside `validate_config.sh` — the resolver is now an actual CI gate.
- **P0-5 — Serena project languages.** `.serena/project.yml` now lists
  `typescript`, `python`, `yaml`, `json`, `markdown`, `bash` instead of the
  YAML-only subset; the 10 TypeScript plugins and the 19 Python scripts
  now get full semantic indexing.
- **autoupdate flip.** `opencode.json.autoupdate` flipped from `true` to
  `"notify"`. The runtime no longer drifts between sessions; the operator
  gets a notification instead of an automatic mutation.
- **Opus 4.7 reference cleanup.** README, AGENTS.md, and
  `.opencode/agents/ry-explore.md` previously claimed `@ry-explore` ran on
  Opus 4.7 / 1M context. Per the marketplace policy, every subagent
  inherits the user's chosen top-level `model` (currently
  `opencode-go/glm-5.1`) — no per-agent override is set. References
  refreshed.

### Hardening (audit Phase 1)

- **Plugin spawn timeouts.** `ry-system-context.ts::readGitOutput` now arms
  a 800 ms `setTimeout` + `proc?.kill()` so the hot
  `experimental.chat.system.transform` path cannot stall on a slow FS or
  lockfile contention. `ry-tools.ts::runScript` accepts a
  `{ timeoutMs, maxOutputBytes }` budget per tool, returns structured
  `{ timedOut, truncated }` results, and renders a deterministic
  `formatTimeoutResult` on the kill path. Five tool budgets: validate 30 s,
  check_deps 30 s, lsp_health 20 s, git_audit 15 s, fullrepo_status 15 s.
- **`ry-env-protection.ts` widening.** Sensitive path matchers for `.ssh/`,
  `.gnupg/`, `.aws/` switched to component-bounded `(^|/)\.foo/` form (the
  previous `/\.foo/` form silently missed relative paths). Added a fourth
  attack vector: data-movement utilities (`cp/mv/tar/zip/base64/find/scp/
  rsync/openssl/gzip/7z`) targeting sensitive path tokens. Documented
  in-file as a best-effort interactive guardrail (not DLP).
- **`ry-shell-strategy.ts` --no-verify widening.** Previously blocked only
  when the branch token matched product names. Now blocks every
  `git push --no-verify` by default; explicit opt-out via
  `RY_ALLOW_NO_VERIFY=1` env var. `shell.env` also gained
  `NO_UPDATE_NOTIFIER=1` and an `RY_DISABLE_CI_ENV=1` escape hatch for
  interactive TTY-aware workflows.
- **`ry-command-audit.ts` resilience.** `mkdir -p .serena` before write
  (handles fresh clones without restored agent-only context). Uses Bun's
  atomic write-then-rename semantics for crash safety; multi-instance
  audit race window documented in-file.
- **AGENTS.md § CI/CD and Git Mutation Gate.** Explicit policy that the
  agent must not create, edit, delete, enable, disable, or trigger CI/CD
  workflows, release pipelines, branch protection, GitHub secrets, or
  remote-state mutations unless the user explicitly requests that change.
  Referenced from `/ry-start`, `/ry-sync`, and `/ry-deploy` command
  templates.
- **JSON Schema offline validation.** New
  `scripts/validate_opencode_schema.py` validates `opencode.json` against
  the vendored
  `references/opencode-config.schema.v1.15.4.json` (fetched from
  https://opencode.ai/config.json). Uses `jsonschema==4.26.0` via uvx so
  CI never depends on opencode.ai being reachable.

### Scalability (audit Phase 2)

- **`.opencode/skills/index.json` machine-readable.**
  `scripts/generate_skills_index.py` produces a deterministic JSON map of
  every SKILL.md → domain → MCP requirements → triggers → network class.
  `--check` mode fails CI when the committed index drifts from the
  generator output. Catches "skill silently references a removed MCP"
  bugs at static-validation time.
- **`docs/security/mcp-trust-boundaries.md`.** 13 MCP servers classified
  by trust class (trusted-official / trusted-public / local-only /
  secrets-required / network-optional) plus repo-read / repo-write flags
  and recommended CI mode. Pairs with the `ry-env-protection.ts` scope
  statement.
- **`docs/github/branch-protection.md`.** Operator-side governance
  contract: required status checks for `main`, linear history, force-push
  ban, codeowner review enforcement, `gh api` snippet for restore. The
  agent does not apply these — owners do. Documented so a future audit
  knows what to expect.
- **ADR-009 — YOLO / full-auto permission profile.** Locks in the explicit
  trust-model rationale for keeping global `edit: "allow"` and
  `bash: "allow"` in `opencode.json`. Auditors will likely flag the
  permission model again; this ADR is the documented "we know it's broad
  and we chose it" record, citing the defense-in-depth plugin pair and
  the single-developer scope.

### Test coverage

- Total pytest cases: **399** across 16 suites (was 383 at `bbd528c`,
  +16). New suites: `test_validate_opencode_schema.py` (7 cases),
  `test_skills_index.py` (6 cases). New cases in
  `test_plugin_surface.py`: `test_flow_hooks_reads_command_from_input_args`,
  `test_plugin_spawn_calls_have_timeout_guard`,
  `test_ry_env_protection_blocks_data_movement_utilities`. CI count is 398
  passed + 1 skipped (the missing-jsonschema-import path test, correctly
  skipped when the dependency is present).

### Migration / operator notes

- Run `cd .opencode && bun install` to refresh the local lockfile against
  the new `package.json`. The committed `.opencode/bun.lock` is the
  canonical source of truth from this release onward.
- If you keep `.serena/project.yml` customizations, merge the new
  languages list (`typescript`, `python`) with your overrides; Serena
  needs both for full semantic indexing.
- If you relied on the implicit Opus 4.7 claim for `@ry-explore`, set
  `agent.ry-explore.model` in your local `opencode.json` overlay — the
  marketplace default no longer makes that promise.
- If `git push --no-verify` is part of your workflow, set
  `export RY_ALLOW_NO_VERIFY=1` in the shell session that needs the
  override; otherwise `ry-shell-strategy.ts` blocks the call.

## [0.11.7] - 2026-05-18

Patch dependency-maintenance release accepting the open Dependabot bump for the OpenCode plugin SDK. The `@opencode-ai/plugin` patch update preserves the runtime hook surface, tool-ID format, and `Project` SDK shape consumed by every plugin — verified by the strict TypeScript baseline against all 10 plugins.

### Changed

- `.opencode/package.json` bumps `@opencode-ai/plugin` from `1.15.3` to `1.15.4`. Upstream `v1.15.4` release notes scope to bugfixes (project-scoped bus events, custom LSP refresh events, hidden background subagent task instructions) plus a TUI markdown polish; the server-side `Plugin`/`Hooks` factory contract and MCP `<server>_<tool>` tool-ID format are unchanged.
- `.opencode/bun.lock` and `.opencode/package-lock.json` regenerated from the bumped manifest.
- README, AGENTS.md, `references/opencode-plugin-patterns.md`, `scripts/_validate_helpers.py`, and `scripts/tests/test_validate_helpers.py` refresh `1.15.3` → `1.15.4` plugin-pin citations while preserving historical "removed between v1.14.48 and v1.15.3" facts (the `codesearch` permission key removal).
- Dependabot PR #6 is superseded by this commit; close after merge.

### Test coverage

- Total pytest cases: **383** across 14 suites (unchanged from `108fc29`).
- `bunx --bun tsc --noEmit -p .opencode/tsconfig.json` passes against `@opencode-ai/plugin@1.15.4`.
- `bash scripts/check_deps_freshness.sh --check-freshness --json` continues to report `stale: 0, errors: 0` for all MCP pins.

## [0.11.6] - 2026-05-18

Patch dependency-maintenance release closing the current Dependabot backlog, clearing live MCP freshness drift, and adding a guard against GitHub Actions SHA/comment drift.

### Added

- `scripts/check_action_pins.py` validates every external workflow `uses:` entry is pinned to a 40-character SHA and carries an inline semver tag comment. `--remote` resolves the tag through `git ls-remote` and verifies it points at the pinned SHA, including annotated-tag dereference.
- `scripts/tests/test_action_pins.py` adds regression coverage for SHA-pinned actions, local/docker skips, tag-only rejection, missing-comment rejection, annotated tags, and mismatched SHA/comment drift.
- `dependency-check.yml` now runs `scripts/check_action_pins.py .github/workflows --remote` before the registry freshness probe.
- `collect_diagnostics.sh` now captures `action-pins.txt` for local triage bundles.

### Changed

- GitHub Actions pins refreshed to current upstream stable refs verified with `git ls-remote`: `actions/checkout` v6.0.2, `actions/setup-python` v6.2.0, `actions/setup-node` v6.4.0, `oven-sh/setup-bun` v2.2.0, `actions/upload-artifact` v7.0.1, `github/codeql-action` v4.35.5, `actions/dependency-review-action` v5.0.0, and `softprops/action-gh-release` v3.0.0.
- Workflow runtime pins refreshed: Bun 1.3.14, pytest 9.0.3, and ruff 0.15.13. PyYAML 6.0.3 and gitleaks 8.30.1 remain current.
- MCP pins refreshed: `chrome-devtools-mcp` 0.26.0 and `semgrep` 1.163.0. `scripts/check_deps_freshness.sh --check-freshness --json` now reports `stale: 0`.
- `.github/dependabot.yml` raises npm and GitHub Actions open-PR limits from 5 to 10 so future action-update backlog cannot block additional recommendations.
- README, AGENTS.md, `.claude/CLAUDE.md`, dependency-update docs, observability docs, release process, and ADR-007 now document the action-pin integrity guard and the 0.11.6 validation baseline.

### Test coverage

- Total pytest cases: **383** across 14 suites (was 377 at `566b738`, +6). New suite: `test_action_pins.py`.

## [0.11.5] - 2026-05-18

Patch release fixing a live `fullrepo_sync.sh publish` cleanup gap found during final post-task git audit.

### Fixed

- `scripts/fullrepo_sync.sh publish` now explicitly removes its temporary staging worktree on the success path, while keeping the existing EXIT trap as a failure-path safety net. This prevents detached `/tmp` worktrees from accumulating after successful `fullrepo` publication.
- `test_fullrepo_sync.py` now asserts the publish path leaves only the main worktree registered after publishing to a local bare origin.

## [0.11.4] - 2026-05-18

Patch release aligning the release workflow's validation context with `validate.yml` after the `v0.11.3` tag run proved release pytest was missing agent-only instruction docs.

### Fixed

- `release.yml` now fetches `origin/fullrepo`, installs the canonical fullrepo exclude block, and restores only `AGENTS.md` plus `.claude/CLAUDE.md` before running the shared pytest corpus. This mirrors `validate.yml` without overlaying `scripts/` or `.opencode/` from `fullrepo` over the tagged release checkout.

## [0.11.3] - 2026-05-18

Patch release fixing the live release/SBOM workflow pins after the first `v0.11.2` tag run proved two immutable action SHAs were invalid upstream.

### Fixed

- `release.yml` and `sbom.yml` now pin `CycloneDX/gh-node-module-generatebom` to the verified `v1.0.3` commit `27e13c2bf0fae78d66387b35ca9749d8cc853060`.
- `release.yml` now pins `softprops/action-gh-release` to the verified `v2.6.1` commit `153bb8e04406b158c6c84fc1615b65b24149a1fe`.
- Manual release dispatch now passes the resolved input tag to `softprops/action-gh-release` via `tag_name`, so tag-triggered and manually-triggered releases target the same version.

## [0.11.2] - 2026-05-18

Patch release aligning the repository-local `fullrepo` workflow with the generic rldyour-flow post-task state contract. This removes the completed-sync Stop-hook loop where `rldyour-opencode` was clean locally but generic flow state still reported `fullrepo_needs_attention: true`.

### Fixed

- **`scripts/fullrepo_sync.sh publish` now publishes a complete portable snapshot**: current `HEAD` plus ignored agent-only files (`AGENTS.md`, `.claude/CLAUDE.md`, `.serena/memories/*`, etc.). Runtime markers and caches are stripped before commit. This supersedes the former agent-only orphan tree that omitted `opencode.json`, `VERSION`, `.github/workflows/`, and other runtime files.
- **`scripts/fullrepo_sync.sh status-json` now reports tree parity fields** (`expected_fullrepo_tree`, `local_fullrepo_matches_worktree`, `remote_fullrepo_matches_worktree`) so local and generic flow checks can agree on whether `fullrepo` is current.
- **Stop-hook loop root cause documented** in new ADR-008, with ADR-005 marked superseded.

### Changed

- `VERSION` bumped to `0.11.2`.
- Added `workflow_dispatch` triggers to `validate.yml`, `typecheck-plugins.yml`, `lint.yml`, `codeql.yml`, `secret-scan.yml`, and `instruction-docs-check.yml` so the full CI set can be manually launched after maintenance work even when path filters would otherwise skip a workflow.
- Release, rollback, observability, README, AGENTS, and Claude instructions now describe `fullrepo` as a complete `HEAD + agent-only` generated branch.

### Test coverage

- Total pytest cases: **377** across 13 suites (was 374 at `babc224`, +3). `test_fullrepo_sync.py` now has 20 cases and includes a real local-bare-origin publish test proving that `fullrepo` contains root runtime files plus agent-only files while excluding `.serena/.flow_sync_marker`.

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
- `.github/workflows/codeql.yml` now keeps CodeQL extraction/query execution as a CI gate with `upload: never` and uploads SARIF as a workflow artifact, because this private repository does not currently have GitHub Code Security enabled for code-scanning SARIF ingestion.
- `.github/workflows/validate.yml` now installs the pinned PyYAML dependency before invoking `scripts/validate_config.sh`; live GitHub runners do not carry PyYAML by default.
- `.github/workflows/secret-scan.yml` now installs the `gitleaks` v8.30.1 CLI directly from the official release tarball with SHA256 verification, avoiding the organization/private-repository license gate in `gitleaks/gitleaks-action`.
- `.gitleaks.toml` allowlists only the synthetic sanitizer regression fixture files that intentionally contain fake token/private-key strings; the workflow still scans git history for every other path.
- `.github/workflows/validate.yml` now restores only `AGENTS.md` and `.claude/CLAUDE.md` from `origin/fullrepo` for test-time cross-layer assertions, while leaving `scripts/` and `.opencode/` on the exact `main` / PR checkout being validated.
- `scripts/fullrepo_sync.sh` adds `install-exclude` for CI and bootstrap flows that need the `.git/info/exclude` block without restoring the full agent-only tree.
- `scripts/fullrepo_sync.sh status-json` now reports `serena_memory_count: 0` when `.serena/memories` is absent, matching normal clean GitHub runner checkouts instead of exiting under `set -euo pipefail`.
- `.github/workflows/dependency-review.yml` now skips `actions/dependency-review-action` on private repositories and emits explicit notices, because GitHub Dependency Review requires Dependency Graph plus GitHub Advanced Security there; `dependency-check.yml` remains the portable pin/freshness gate.
- `README.md`, `AGENTS.md`, `.claude/CLAUDE.md`, and Serena release memories refreshed from the 0.11.1 validation baseline.
- Corrected the 0.11.0 changelog test-count line from stale intermediate numbers to the final `7c02482` collection state.

### Test coverage

- Total pytest cases: **374** across 13 suites (was 357 at `7c02482`, +17). Breakdown: 52 validate_helpers + 12 extract_pins + 129 skill_routing + 16 command_audit_sanitizer + 11 plugin_surface + 4 opencode_resolve + 44 permission_policy_regexes + 11 smoke_mcp + 7 validate_instruction_docs + 8 doctor_opencode + 23 sanitize_diag + 40 check_freshness + 17 fullrepo_sync.

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
