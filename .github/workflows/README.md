# GitHub Actions Workflows

Fifteen workflows provide the public/free CI surface for the OpenCode adapter.
The repository is public, so standard GitHub-hosted runners do not consume the
owner's private-repository Actions minutes. Keep every workflow on standard
runner labels and keep third-party actions pinned to full commit SHAs.

## Required PR Gates

| Workflow | Purpose |
| --- | --- |
| `validate.yml` | Core OpenCode config, schema, MCP, index, doctor, and unit-test validation. |
| `cross-platform.yml` | Lightweight metadata/path smoke on standard Ubuntu, Windows, and macOS public runners. |
| `instruction-docs-check.yml` | Agent instruction-doc presence and drift checks. |
| `lint.yml` | Ruff lint on Python maintenance scripts. |
| `typecheck-plugins.yml` | Strict TypeScript typecheck for local OpenCode plugins. |
| `opencode-runtime.yml` | Installed-runtime smoke for OpenCode-specific behavior. |
| `actionlint.yml` | GitHub Actions syntax and expression lint. |
| `codeql.yml` | CodeQL code scanning for Python and TypeScript. |
| `semgrep.yml` | Semgrep OSS static analysis for Python, TypeScript, workflows, CI, and secrets. |
| `secret-scan.yml` | Gitleaks history scan for accidental secrets. |
| `dependency-review.yml` | Pull-request dependency diff review. |

## Supply-Chain And Drift Gates

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `scorecard.yml` | push, weekly, manual, branch-protection changes | OpenSSF Scorecard JSON artifact/check-mode supply-chain signal. |
| `dependency-check.yml` | weekly/manual | Dependency pin and MCP capability freshness. |
| `sbom.yml` | weekly/manual | CycloneDX SBOM evidence for OpenCode runtime dependencies. |

## Release Gate

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `release.yml` | numeric product tag or manual dispatch | Release validation, TypeScript typecheck, SBOM artifact, GitHub Release. |

## Cost Policy

- Public adapter CI must stay on standard GitHub-hosted runner labels only.
- No self-hosted, larger, runner-group, ARC, private organization, or paid-size
  runner labels.
- The public/free baseline includes one lightweight cross-platform workflow on
  standard Ubuntu, Windows, and macOS runners. Runtime-heavy and release jobs
  may stay Ubuntu-only when the local script is OS-independent or the required
  toolchain is Linux-only.
- Workflow artifacts must set explicit retention and stay at or below 30 days.
- Path-filtered and scheduled jobs keep signal focused while preserving full
  public/free coverage.
