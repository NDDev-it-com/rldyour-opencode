# Branch Protection and Required Checks

This document fixes the **operator-side governance contract** for the
`NDDev-it-com/rldyour-opencode` repository. The agent does not apply these
rules — owners do, via the GitHub web UI or `gh api`. The contract is
captured here so future audits and successor maintainers know what to
restore if branch protection is ever reset.

## Protected branches

- `main` — product/runtime branch; only branch from which `release.yml`
  fires; the source for `fullrepo` snapshots.
- `fullrepo` — generated complete-state branch (`HEAD` + agent-only
  overlay). Never accept human pull requests targeting `fullrepo`; the
  branch is `--force-with-lease`-pushed by `scripts/fullrepo_sync.sh`
  from a verified `main` snapshot.

## Required status checks for `main`

The following workflow names must be required for any PR targeting `main`.
The list mirrors the `.github/workflows/` set and stays in sync with the
roadmap in `docs/decisions/007-ci-mirrors-local-validation.md`.

| Workflow | Job | Required | Notes |
|---|---|---|---|
| `Validate rldyour-opencode` (`validate.yml`) | `validate` | yes | runs `scripts/validate_config.sh` + pytest |
| `Typecheck Plugins` (`typecheck-plugins.yml`) | `typecheck` | yes | strict TS against all 10 plugins |
| `Lint` (`lint.yml`) | `ruff` | yes | Python lint for `scripts/` |
| `Instruction Docs Check` (`instruction-docs-check.yml`) | `validate-instruction-docs` | yes | path-filtered |
| `Dependency Freshness` (`dependency-check.yml`) | `dependency-check` | yes | weekly + dispatch; required also on PR |
| `Secret Scan` (`secret-scan.yml`) | `gitleaks` | yes | gitleaks CLI tarball |
| `CodeQL` (`codeql.yml`) | `analyze` | yes | artifact-only until GHAS is enabled |
| `OpenCode Runtime` (`opencode-runtime.yml`) | `runtime` | yes (new in 0.12.0) | installs pinned opencode-ai@1.15.4 and runs `opencode debug config` |
| `Dependency Review` (`dependency-review.yml`) | `dependency-review` | optional | skipped on private repos without GHAS |
| `SBOM Snapshot` (`sbom.yml`) | `sbom` | optional | runs on `release` events |
| `Release` (`release.yml`) | `release` | n/a | tag-triggered |

## Additional protections

- **Linear history**: required. Squash-and-merge or rebase-and-merge only;
  no merge commits on `main`.
- **Conversation resolution**: required before merge.
- **Restrict pushes**: only repository administrators may push directly to
  `main`; everyone else opens a PR.
- **Allow force pushes**: disabled for `main` and `fullrepo`. `fullrepo` is
  force-pushed by the maintainer via `scripts/fullrepo_sync.sh publish`
  using `--force-with-lease`; this is performed locally, not via PR.
- **Allow deletions**: disabled for `main` and `fullrepo`.
- **Required pull request reviews**: 1 reviewer for single-developer
  ownership (`@rldyourmnd`) with codeowner enforcement via `.github/CODEOWNERS`.
- **Dismiss stale reviews when new commits are pushed**: enabled.
- **Require review from codeowners**: enabled (CODEOWNERS maps every path
  to `@rldyourmnd`).

## Restoring protection

```bash
# Read-only inspection:
gh api repos/NDDev-it-com/rldyour-opencode/branches/main/protection | jq

# Apply minimum protection (single-developer profile, contains required checks):
gh api -X PUT repos/NDDev-it-com/rldyour-opencode/branches/main/protection \
  -F required_status_checks.strict=true \
  -F required_status_checks.contexts[]='Validate rldyour-opencode' \
  -F required_status_checks.contexts[]='Typecheck Plugins' \
  -F required_status_checks.contexts[]='Lint' \
  -F required_status_checks.contexts[]='Instruction Docs Check' \
  -F required_status_checks.contexts[]='Dependency Freshness' \
  -F required_status_checks.contexts[]='Secret Scan' \
  -F required_status_checks.contexts[]='CodeQL' \
  -F required_status_checks.contexts[]='OpenCode Runtime' \
  -F enforce_admins=false \
  -F required_pull_request_reviews.required_approving_review_count=1 \
  -F required_pull_request_reviews.dismiss_stale_reviews=true \
  -F required_pull_request_reviews.require_code_owner_reviews=true \
  -F required_linear_history=true \
  -F allow_force_pushes=false \
  -F allow_deletions=false \
  -F restrictions=null
```

The agent must NOT execute these commands unattended. Branch protection
mutations require explicit user authorization in the same request (see
AGENTS.md § CI/CD and Git Mutation Gate).
