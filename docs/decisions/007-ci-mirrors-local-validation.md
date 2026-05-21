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

CI baseline is an 11-workflow set under `.github/workflows/` plus `.github/dependabot.yml`. Each workflow follows the same hardening contract:

- Actions pinned to commit SHA with an inline `# vN.M.K` comment naming the resolved tag.
- Workflow-level `permissions:` block declares minimal scope (typically `contents: read`); job-level overrides only where strictly required (`contents: write` for release). Because this repository is public, CodeQL uses `actions: read` + `security-events: write` so SARIF is uploaded to GitHub code scanning alerts. The workflow still keeps the SARIF output directory as a downloadable artifact for offline audit/debugging.
- `concurrency:` group on workflow + ref, with `cancel-in-progress: true` for non-release flows.
- `timeout-minutes:` on every job (5-20 minutes depending on scope).
- For surfaces that can portably express it, `strategy.matrix.os: [ubuntu-latest, macos-latest]` so script regressions are caught on the owner's actual development matrix.
- Public repositories use automatic CI/CD by default. The runtime policy lives in `references/public-repo-ci-policy.md` and is loaded by OpenCode through `opencode.json.instructions`. Private repositories keep the manual trigger default.

Workflow set:

| Workflow | Trigger | Matrix | Purpose |
|---|---|---|---|
| `validate.yml` | push + PR + manual dispatch | Linux + macOS | runs `scripts/validate_config.sh` and the pytest corpus; shell-strict-mode lint job |
| `dependency-check.yml` | weekly cron + dispatch | Linux | pin report + GitHub Actions SHA/comment integrity + network freshness + MCP smoke |
| `instruction-docs-check.yml` | path-filtered + manual dispatch | Linux | `validate_instruction_docs.py` (skips on normal-branch PRs that lack the agent-only files) |
| `typecheck-plugins.yml` | path-filtered + manual dispatch | Linux + macOS | `bun install --frozen-lockfile && bunx --bun tsc --noEmit -p .opencode/tsconfig.json` |
| `lint.yml` | path-filtered + manual dispatch | Linux + macOS | ruff against `scripts/` |
| `codeql.yml` | push + PR + weekly + manual dispatch | Linux + macOS | javascript-typescript + python analysis using `.github/codeql/codeql-config.yml` so hidden `.opencode/plugins` TypeScript is included; SARIF is uploaded to code scanning with an OS+language category and also kept as a workflow artifact |
| `secret-scan.yml` | push + PR + manual dispatch | Linux | gitleaks CLI release tarball with SHA256 verification, `.gitleaks.toml` fixture allowlist, and checkout fetch-depth: 0 |
| `dependency-review.yml` | PR | Linux | actions/dependency-review-action, fail-on-severity: moderate |
| `release.yml` | numeric `X.Y.Z` tag + dispatch | Linux + macOS | full validation + typecheck + tag-vs-VERSION check + npm SBOM generation + GitHub Release on Linux |
| `sbom.yml` | release published + dispatch | Linux | standalone CycloneDX SBOM artifact |
| `opencode-runtime.yml` | push + PR + dispatch | Linux + macOS | installs the pinned OpenCode CLI and verifies `opencode debug config` / runtime resolver behavior |

Dependabot watches `npm` (`.opencode/`) and `github-actions` (`/`) on a weekly cadence, capped at 10 open PRs per ecosystem; both use scoped Conventional Commits prefixes (`chore(deps)`, `chore(ci)`). `scripts/check_action_pins.py` is the local guard that enforces each workflow `uses:` pin is a 40-character SHA and, in `--remote` mode, that the inline `# vX.Y.Z` comment resolves to that SHA.

## Consequences

Positive:

- CI and local validation share the same scripts. A `bash scripts/validate_config.sh` pass locally is what CI runs; no divergence.
- Owner-platform parity: Linux + macOS matrix catches script portability regressions before they hit a local checkout.
- Supply-chain hardening explicit: SHA-pinned actions, least-privilege permissions, dependency review, gitleaks, CodeQL, SBOM.
- Release flow is gated: tag must match `VERSION`, full test corpus + typecheck must be green on Linux and macOS, SBOM is generated with `npm sbom` and attached to the release.

Negative:

- Workflow count grew from 2 to 10. Cognitive load on contributors is higher, mitigated by the consistent hardening pattern across all files and by `CONTRIBUTING.md` documenting the gate set.
- macOS matrix doubles runtime on touched surfaces. Because the upstream
  repository is public and uses only standard runners, these jobs do not consume
  paid private-repository Actions minutes; still, OS-independent gates such as
  dependency review and gitleaks stay Ubuntu-only.
- Some non-GitHub release surfaces (gitleaks CLI tarball and npm SBOM behavior) require periodic re-verification. Mitigation: keep explicit version/checksum comments where external binaries are downloaded, use dependabot's `github-actions` ecosystem watcher for action pins, keep `scripts/check_action_pins.py --remote` green, and keep the `npm sbom` release step covered by tag-triggered Linux/macOS release runs.
- `.gitleaks.toml` is intentionally narrow: it allowlists only sanitizer regression fixture files that contain fake token/private-key strings by design; do not add broad token regex allowlists.
- CodeQL SARIF is uploaded to code scanning on public runs, so the Security tab and branch protection can observe real alerts instead of artifact-only analysis. The SARIF artifact remains a secondary audit output.
- GitHub Dependency Review runs on PRs and fails the check on severity policy when Dependency Graph is available; if not available, check semantics follow action output.

## Compliance

- 0.11.0 group I implements the workflow set + dependabot.
- 0.11.0 group H implements the `.opencode/tsconfig.json` that `typecheck-plugins.yml` consumes.
- 0.11.0 groups A-G implement the local scripts that all workflows wrap.
- 0.11.6 adds `scripts/check_action_pins.py` as the local + CI guard for SHA-pinned action comments and Dependabot action-update drift.
- `scripts/tests/test_fullrepo_sync.py::test_script_has_strict_bash_header` enforces the shell strictness contract that `validate.yml::shell-strict-mode` also asserts at CI time.

## Future work

- Wire OIDC-based npm provenance once the marketplace publishes to a registry (out of scope today; SBOM-only release is sufficient for the current distribution model).
- Add Sigstore signed releases once the workflow set proves stable in production for one minor release.
- If a private fork disables GitHub Code Security, operators may need to adapt CodeQL upload permissions in that fork. The public upstream keeps real code-scanning upload enabled.
- Public PR hardening target is already in place; keep watch over Dependency Graph outages and action behavior on action-provider changes.
- Evaluate adding a scheduled macOS smoke that exercises the LSP installer (`check_lsps.sh` + `install_lsps.sh`) against the actual `brew` toolchain.
