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

## Public repository CI/CD

`NDDev-it-com/rldyour-opencode` is public, so existing CI/CD workflows are
automatic by default. `references/public-repo-ci-policy.md` is loaded by
OpenCode through `opencode.json.instructions`; it authorizes running existing
workflow surfaces for public-repo verification while keeping workflow edits,
branch protection changes, repository rulesets, environments, secrets, and
variables owner-restricted.

## Required status checks for `main`

The contexts below match what GitHub emits at runtime. Audit P0-5 closed
the previous docs/runtime drift by deriving the table from the same
workflow files using `scripts/print_required_check_contexts.sh`. Re-run
that script after any workflow edit and update this table verbatim — a
required check context that does not match a real GitHub check name
will block all merges (the protection rule waits for a context that
never fires) or, worse, silently let a regression through (the
required check name was a typo and never gated anything).

### How to refresh this table

```bash
bash scripts/print_required_check_contexts.sh --json | jq -r '
  .contexts[]
  | [.workflow_name, .job_key, .context, (.triggers | join(","))]
  | @tsv
'
```

Compare the output against the rows below. Any mismatch is a docs bug
fix candidate, not a workflow bug.

### Required on every pull request to `main`

| Workflow file | Workflow name | Job | GitHub check context |
|---|---|---|---|
| `validate.yml` | `Validate rldyour-opencode` | `validate` (matrix `os: [ubuntu-latest, macos-latest]`) | `Validate rldyour-opencode / validate (ubuntu-latest)` and `Validate rldyour-opencode / validate (macos-latest)` |
| `validate.yml` | `Validate rldyour-opencode` | `shell-strict-mode` | `Validate rldyour-opencode / shell-strict-mode (ubuntu-latest)` and `Validate rldyour-opencode / shell-strict-mode (macos-latest)` |
| `typecheck-plugins.yml` | `Typecheck Plugins` | `typecheck` (matrix `os: [ubuntu-latest, macos-latest]`) | `Typecheck Plugins / typecheck (ubuntu-latest)` and `Typecheck Plugins / typecheck (macos-latest)` |
| `lint.yml` | `Lint` | `ruff` (matrix `os: [ubuntu-latest, macos-latest]`) | `Lint / ruff (ubuntu-latest)` and `Lint / ruff (macos-latest)` |
| `instruction-docs-check.yml` | `Instruction Docs Check` | `instruction-docs` | `Instruction Docs Check / instruction-docs (ubuntu-latest)` and `Instruction Docs Check / instruction-docs (macos-latest)` |
| `secret-scan.yml` | `Secret Scan` | `gitleaks` | `Secret Scan / gitleaks` |
| `codeql.yml` | `CodeQL` | `analyze` (matrix `os: [ubuntu-latest, macos-latest]`, `language: [javascript-typescript, python]`) | `CodeQL / Analyze (ubuntu-latest / javascript-typescript) (ubuntu-latest, javascript-typescript)` and `CodeQL / Analyze (ubuntu-latest / python) (ubuntu-latest, python)` and `CodeQL / Analyze (macos-latest / javascript-typescript) (macos-latest, javascript-typescript)` and `CodeQL / Analyze (macos-latest / python) (macos-latest, python)` |
| `opencode-runtime.yml` | `OpenCode Runtime` | `runtime` (matrix `os: [ubuntu-latest, macos-latest]`) | `OpenCode Runtime / runtime (ubuntu-latest)` and `OpenCode Runtime / runtime (macos-latest)` |

### Scheduled / manual / artifact only (NOT required PR contexts)

These workflows do not run on PR by design, so listing them as required
PR contexts would deadlock merges. They are tracked for visibility and
restored separately if branch protection is reset.

| Workflow file | Workflow name | Job | Trigger | Notes |
|---|---|---|---|---|
| `dependency-check.yml` | `Dependency Freshness` | `freshness` | schedule + workflow_dispatch | weekly pin + freshness probe + remote-head/local-launch MCP smoke; not gated on PR |
| `dependency-review.yml` | `Dependency Review` | `dependency-review` | pull_request | runs on pull requests; pass/fail follows repository Dependency Graph availability and action outcome |
| `sbom.yml` | `SBOM Snapshot` | `cyclonedx` | release + workflow_dispatch | optional artifact |
| `release.yml` | `Release` | `verify` | tag push + workflow_dispatch | tag-triggered, not PR-required |

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

The required-context list below mirrors the PR-required rows above and
expands every matrix axis explicitly — GitHub branch protection
requires the FULL context name including matrix params.

```bash
# Read-only inspection:
gh api repos/NDDev-it-com/rldyour-opencode/branches/main/protection | jq

# Apply minimum protection (single-developer profile, contains required checks):
gh api -X PUT repos/NDDev-it-com/rldyour-opencode/branches/main/protection \
  -F required_status_checks.strict=true \
  -F required_status_checks.contexts[]='Validate rldyour-opencode / validate (ubuntu-latest)' \
  -F required_status_checks.contexts[]='Validate rldyour-opencode / validate (macos-latest)' \
  -F required_status_checks.contexts[]='Validate rldyour-opencode / shell-strict-mode (ubuntu-latest)' \
  -F required_status_checks.contexts[]='Validate rldyour-opencode / shell-strict-mode (macos-latest)' \
  -F required_status_checks.contexts[]='Typecheck Plugins / typecheck (ubuntu-latest)' \
  -F required_status_checks.contexts[]='Typecheck Plugins / typecheck (macos-latest)' \
  -F required_status_checks.contexts[]='Lint / ruff (ubuntu-latest)' \
  -F required_status_checks.contexts[]='Lint / ruff (macos-latest)' \
  -F required_status_checks.contexts[]='Instruction Docs Check / instruction-docs (ubuntu-latest)' \
  -F required_status_checks.contexts[]='Instruction Docs Check / instruction-docs (macos-latest)' \
  -F required_status_checks.contexts[]='Secret Scan / gitleaks' \
  -F required_status_checks.contexts[]='CodeQL / Analyze (ubuntu-latest / javascript-typescript) (ubuntu-latest, javascript-typescript)' \
  -F required_status_checks.contexts[]='CodeQL / Analyze (ubuntu-latest / python) (ubuntu-latest, python)' \
  -F required_status_checks.contexts[]='CodeQL / Analyze (macos-latest / javascript-typescript) (macos-latest, javascript-typescript)' \
  -F required_status_checks.contexts[]='CodeQL / Analyze (macos-latest / python) (macos-latest, python)' \
  -F required_status_checks.contexts[]='OpenCode Runtime / runtime (ubuntu-latest)' \
  -F required_status_checks.contexts[]='OpenCode Runtime / runtime (macos-latest)' \
  -F enforce_admins=false \
  -F required_pull_request_reviews.required_approving_review_count=1 \
  -F required_pull_request_reviews.dismiss_stale_reviews=true \
  -F required_pull_request_reviews.require_code_owner_reviews=true \
  -F required_linear_history=true \
  -F allow_force_pushes=false \
  -F allow_deletions=false \
  -F restrictions=null
```

The agent must NOT execute these branch-protection mutation commands
unattended. Branch protection mutations require explicit user authorization in
the same request (see AGENTS.md § CI/CD and Git Mutation Gate). This remains
true even though public-repo CI workflow execution itself is automatic by
policy.

## Verification

`scripts/print_required_check_contexts.sh` is the authoritative source.
The table above is generated from the workflow files; rerun the script
after every workflow change and update this document if any context
name has drifted. CI does not yet fail on a docs/runtime mismatch (the
docs are operator-facing, not gated), but the script makes the drift
trivial to spot during review.
