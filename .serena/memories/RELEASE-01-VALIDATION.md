<!-- Memory Metadata
Last updated: 2026-05-17
Last commit: 45e5539 chore(serena): sync project knowledge after cda4c1d
Scope: scripts/, scripts/tests/, .github/workflows/, docs/release-process.md, docs/dependency-updates.md, docs/observability.md, VERSION, CHANGELOG.md
Area: RELEASE
-->

# RELEASE-01-VALIDATION

## Purpose

Validation, diagnostics, release, and dependency-update contracts for the OpenCode marketplace.

## Source Of Truth

- `scripts/validate_config.sh` and `scripts/_validate_helpers.py`: local config/frontmatter/version validator.
- `scripts/tests/`: pytest suites that cover validators, plugin surface, OpenCode resolution, skill routing, permission regexes, MCP smoke behavior, and instruction docs.
- `.github/workflows/validate.yml`: CI validation workflow.
- `.github/workflows/dependency-check.yml`: scheduled dependency and MCP smoke workflow.
- `scripts/check_deps_freshness.sh` and `scripts/_extract_pins.py`: pinned dependency reporting.
- `scripts/smoke_mcp_capabilities.py`: MCP reachability probe.
- `scripts/collect_diagnostics.sh` and `scripts/_sanitize_diag.py`: local diagnostics bundle with redaction.

## Entry Points

- `bash scripts/validate_config.sh`: baseline repository validation.
- `python3 -m pytest scripts/tests/`: full test suite.
- `uvx --from "pytest==9.0.2" pytest scripts/tests/`: pinned pytest invocation used by project docs.
- `scripts/check_deps_freshness.sh --json`: dependency pin report.
- `python3 scripts/smoke_mcp_capabilities.py --json`: MCP capability smoke probe.
- `scripts/collect_diagnostics.sh --include-doctor`: diagnostic bundle plus LSP/OpenCode doctor passes.

## Current Behavior

- There are 17 top-level files in `scripts/` and 9 pytest suites in `scripts/tests/`.
- The expected test suite count remains 259 cases across 9 suites, as documented in `AGENTS.md` and prior validation memories.
- `validate_config.sh` validates `opencode.json`, skill frontmatter, agent frontmatter, command frontmatter, and `VERSION` semver through `_validate_helpers.py`.
- `_extract_pins.py` parses pinned MCP dependencies from `opencode.json`.
- `_sanitize_diag.py` redacts credential patterns used by `collect_diagnostics.sh` before diagnostic output is persisted.
- `smoke_mcp_capabilities.py` treats remote HTTP responses as reachability evidence and treats local process timeout as alive; fast zero exit is indeterminate rather than alive.

## Contracts And Data

- CI actions in `.github/workflows/validate.yml` and `.github/workflows/dependency-check.yml` are pinned to commit SHAs.
- `dependency-check.yml` runs weekly and via `workflow_dispatch`; its MCP smoke step is non-blocking for transient remote issues.
- Diagnostics under `diagnostics/` are local artifacts and should not be committed.
- `VERSION` must match SemVer and `CHANGELOG.md` follows Keep a Changelog.

## Invariants

- Do not report a release-ready or synced state without running the validation commands relevant to touched files, or explicitly reporting why they were blocked.
- Do not bypass `_sanitize_diag.py` when collecting diagnostic output that may include substituted environment values.
- Do not replace pinned dependency reporting with ad hoc grep; use `_extract_pins.py` or its wrapper.

## Change Rules

- Add tests with any schema, hook-surface, permission, command, skill, or instruction-doc behavior change.
- Update `docs/release-process.md`, `docs/dependency-updates.md`, or `docs/observability.md` when release or diagnostics commands change.
- Keep CI and local validation behavior aligned; project docs treat local scripts as the same gates CI runs.

## Verification

- `bash scripts/validate_config.sh`: config/frontmatter/version validation.
- `python3 -m pytest scripts/tests/`: full test suite.
- `python3 scripts/smoke_mcp_capabilities.py --json`: MCP smoke envelope.
- `bash scripts/check_deps_freshness.sh --json`: dependency pin report.
