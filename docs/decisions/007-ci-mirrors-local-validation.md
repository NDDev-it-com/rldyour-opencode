# ADR-007: CI mirrors local validation as thin wrappers

- Status: accepted
- Date: 2026-05-17
- Deciders: @rldyourmnd
- Consulted: ChatGPT 5.5 Pro audit prompt (2026-05-17) + three deep-audit reports + GitHub Actions hardening docs

## Context and Problem Statement

Before 0.11.0 the marketplace had two CI workflows (`validate.yml`, `dependency-check.yml`). The audit identified governance / supply-chain / typecheck gaps that require additional CI surfaces, and the existing workflows had drift hazards: pre-0.11.0 there was no shell-strict-mode lint in CI, no plugin typecheck, no instruction-docs validation, no CodeQL, no gitleaks, no dependency-review, no SBOM, and no release workflow.

A second concern emerged from the audit: when CI logic diverges from local scripts, the marketplace ends up with two implementations of "valid" — one in workflow YAML and one in local bash. That doubles maintenance and creates drift opportunities (the local script can pass while CI fails, or vice versa).

## Decision Drivers

- Owner runs the marketplace on both Linux and macOS, so CI must mirror that matrix for surfaces that can portably express it.
- GitHub Actions docs (Secure Use, Workflow Syntax, Concurrency) prescribe SHA-pinning, least-privilege `permissions:`, concurrency cancel-in-progress, and explicit timeouts as the baseline.
- Audit reports flagged missing CodeQL / gitleaks / dependency-review / SBOM / release-provenance surfaces against OWASP Top 10 2025 categories A02 (Security Misconfiguration), A03 (Supply Chain Failures), and A08 (Software/Data Integrity Failures).
- Single source of truth: local scripts are authoritative; CI calls them.

## Considered Options

1. Local-only validation. Reject — manual gate doesn't scale and doesn't block bad PRs.
2. CI-only validation with custom YAML logic. Reject — doubles the validation surface; local + CI drift becomes a maintenance burden.
3. Local scripts as source of truth; CI workflows as thin wrappers that invoke them with appropriate matrix / permissions / timeouts. **Selected.**

## Decision Outcome

CI baseline is a 10-workflow set under `.github/workflows/` plus `.github/dependabot.yml`. Each workflow follows the same hardening contract:

- Actions pinned to commit SHA with an inline `# vN.M.K` comment naming the resolved tag.
- Workflow-level `permissions:` block declares minimal scope (typically `contents: read`); job-level overrides only where strictly required (`contents: write` for release). CodeQL uses local SARIF artifacts because this private repository does not currently have GitHub Code Security enabled for code-scanning upload.
- `concurrency:` group on workflow + ref, with `cancel-in-progress: true` for non-release flows.
- `timeout-minutes:` on every job (5-20 minutes depending on scope).
- For surfaces that can portably express it, `strategy.matrix.os: [ubuntu-latest, macos-latest]` so script regressions are caught on the owner's actual development matrix.

Workflow set:

| Workflow | Trigger | Matrix | Purpose |
|---|---|---|---|
| `validate.yml` | push + PR | Linux + macOS | runs `scripts/validate_config.sh` and the pytest corpus; shell-strict-mode lint job |
| `dependency-check.yml` | weekly cron + dispatch | Linux | pin report + network freshness + MCP smoke |
| `instruction-docs-check.yml` | path-filtered | Linux | `validate_instruction_docs.py` (skips on normal-branch PRs that lack the agent-only files) |
| `typecheck-plugins.yml` | path-filtered | Linux + macOS | `bun install --frozen-lockfile && bunx --bun tsc --noEmit -p .opencode/tsconfig.json` |
| `lint.yml` | path-filtered | Linux + macOS | ruff against `scripts/` |
| `codeql.yml` | push + PR + weekly | Linux | javascript-typescript + python analysis using `.github/codeql/codeql-config.yml` so hidden `.opencode/plugins` TypeScript is included; SARIF is kept as a workflow artifact instead of uploaded to code scanning |
| `secret-scan.yml` | push + PR | Linux | gitleaks CLI release tarball with SHA256 verification, `.gitleaks.toml` fixture allowlist, and checkout fetch-depth: 0 |
| `dependency-review.yml` | PR | Linux | actions/dependency-review-action, fail-on-severity: moderate |
| `release.yml` | `v*.*.*` tag + dispatch | Linux | full validation + typecheck + tag-vs-VERSION check + SBOM generation + GitHub Release |
| `sbom.yml` | release published + dispatch | Linux | standalone CycloneDX SBOM artifact |

Dependabot watches `npm` (`.opencode/`) and `github-actions` (`/`) on a weekly cadence, capped at 5 open PRs per ecosystem; both use scoped Conventional Commits prefixes (`chore(deps)`, `chore(ci)`).

## Consequences

Positive:

- CI and local validation share the same scripts. A `bash scripts/validate_config.sh` pass locally is what CI runs; no divergence.
- Owner-platform parity: Linux + macOS matrix catches script portability regressions before they hit a local checkout.
- Supply-chain hardening explicit: SHA-pinned actions, least-privilege permissions, dependency review, gitleaks, CodeQL, SBOM.
- Release flow is gated: tag must match `VERSION`, full test corpus + typecheck must be green, SBOM is generated and attached to the release.

Negative:

- Workflow count grew from 2 to 10. Cognitive load on contributors is higher, mitigated by the consistent hardening pattern across all files and by `CONTRIBUTING.md` documenting the gate set.
- macOS matrix doubles the runner-minute usage on touched surfaces. Mitigation: workflows are path-filtered where possible (`typecheck-plugins`, `lint`) so unrelated PRs don't pay the macOS cost.
- Some non-GitHub release pins (gitleaks CLI tarball, CycloneDX action) require periodic re-verification. Mitigation: keep explicit version/checksum comments in workflow docs and use dependabot's `github-actions` ecosystem watcher for action pins.
- `.gitleaks.toml` is intentionally narrow: it allowlists only sanitizer regression fixture files that contain fake token/private-key strings by design; do not add broad token regex allowlists.
- CodeQL SARIF upload to code scanning is intentionally disabled (`upload: never`) until GitHub Code Security is enabled for this private repository. The workflow still runs extraction and queries, then stores SARIF as an Actions artifact.

## Compliance

- 0.11.0 group I implements the workflow set + dependabot.
- 0.11.0 group H implements the `.opencode/tsconfig.json` that `typecheck-plugins.yml` consumes.
- 0.11.0 groups A-G implement the local scripts that all workflows wrap.
- `scripts/tests/test_fullrepo_sync.py::test_script_has_strict_bash_header` enforces the shell strictness contract that `validate.yml::shell-strict-mode` also asserts at CI time.

## Future work

- Wire OIDC-based npm provenance once the marketplace publishes to a registry (out of scope today; SBOM-only release is sufficient for the current distribution model).
- Add Sigstore signed releases once the workflow set proves stable in production for one minor release.
- Enable CodeQL code-scanning SARIF upload if GitHub Code Security is enabled for this repository; until then the SARIF artifact is the auditable output.
- Evaluate adding a scheduled macOS smoke that exercises the LSP installer (`check_lsps.sh` + `install_lsps.sh`) against the actual `brew` toolchain.
