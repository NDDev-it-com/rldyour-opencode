---
description: "Синхронизация Serena memories, AGENTS.md, .opencode и git после meaningful работы. Synchronize memories, docs, and git state."
agent: build
---

Synchronize project state after meaningful work:

1. Serena memory freshness first: invoke @flow-memory-sync to verify and update .serena/memories/ against current code at HEAD.
2. Project instruction docs second: update AGENTS.md when durable project facts changed. Verify instruction docs reflect current code state.
3. Quality checks and manual evidence third: run applicable lint, typecheck, and test commands for the touched scope.
4. Atomic commits fourth: commit source changes by logical feature/fix/refactor units. Commit Serena/docs sync separately when it improves history clarity. Use Conventional Commits.
5. GitHub sync fifth: push to upstream when configured. If upstream is missing, ask before setting it.
6. Repository context check sixth: ensure durable agent context (`AGENTS.md`, `.serena/memories/`, `.serena/project.yml`, `.opencode/`) is tracked on `main` and runtime-local state stays ignored.
7. Branch/worktree cleanup last: remove merged worktrees and branches only after verifying they are merged into main and pushed if needed.

Never commit secrets, runtime markers, browser artifacts, local env files, or accidental generated junk.

## CI/CD and Git Mutation Gate

`/ry-sync` may commit on feature branches and push to upstream when an upstream exists. It must NOT create or modify workflows, branch protection rules, GitHub environments, secrets, tags, or release artifacts unless the user explicitly asks for that mutation. Force-push, `git push --no-verify`, and product-branch (`main`/`master`/`release`/`production`) direct pushes require explicit user authorization in the same request. See AGENTS.md § CI/CD and Git Mutation Gate.

Public repository exception: when the current repository is verified public, existing CI/CD workflows are automatic by default. After public-repo sync pushes, verify the GitHub Actions runs for the same HEAD; if a required readiness/release workflow did not run because it is `workflow_dispatch`, scheduled, or release-only, trigger that existing workflow with `gh workflow run` and wait for completion. Do not edit workflows or GitHub governance surfaces without explicit owner request. See `references/public-repo-ci-policy.md`.

Reply in Russian unless the owner explicitly requests another language.

Reference: references/post-task-sync.md, references/project-instructions-and-adrs.md
