---
description: "Полный lifecycle задачи: init → research → plan → implement → quality gates → reviewer subagents → post-task sync. Full task lifecycle from prompt to reviewed and synced state."
agent: build
---

Implement a task through the full quality workflow:

1. If context is missing, run a scoped ry-init.
2. Understand the prompt and affected scope.
3. Research project code through Serena and project memories.
4. Research current best practices and libraries through @ry-explore when technical uncertainty exists.
5. Pass the context sufficiency gate before editing: code paths, symbols, data contracts, integration points, existing patterns, checks, and research evidence must be known or explicitly marked as unknown.
6. Produce a detailed implementation plan.
7. Verify the plan against real code and adjust until coherent.
8. Create or select branch/worktree and implement through atomic commits.
9. Run progress checkpoints after meaningful milestones or every 2-3 plan groups: compare implementation against the plan, context pack, existing patterns, and touched integration path. Report progress in Russian.
10. Run quality gates and fix all issues in touched scope plus integration path.
11. Run reviewer workflow. Use parallel subagents (flow-architecture-review, flow-quality-review, flow-consistency-review, flow-integration-review, flow-verification-review) for the review phase. Use flow-security-review when the scope is security-sensitive.
12. Run browser/security/design/LSP workflows when triggered by the change type.
13. Synchronize Serena memories, AGENTS.md, instruction docs, git, and fullrepo through /ry-sync.

## CI/CD and Git Mutation Gate

Do not create, edit, delete, enable, disable, or trigger CI/CD workflows, release pipelines, deployment automation, branch protection, GitHub rulesets, GitHub environments, GitHub secrets/variables, remote branch creation/deletion, force-pushes, tag creation/deletion, commits on product branches (`main`/`master`/`release`/`production`), or pull-request merges unless the user explicitly asks for that change in the current request. Running existing read-only validation commands is always allowed. See AGENTS.md § CI/CD and Git Mutation Gate.

Public repository exception: when the current repository is verified public, existing CI/CD workflows are automatic by default. After pushing or tagging public-repo changes, verify the GitHub Actions runs for the same HEAD/tag; if a required readiness/release workflow did not run because it is `workflow_dispatch`, scheduled, or release-only, trigger that existing workflow with `gh workflow run` and wait for completion. Do not edit workflows or GitHub governance surfaces without explicit owner request. See `references/public-repo-ci-policy.md`.

Reference: references/flow-lifecycle.md, references/context-sufficiency-gate.md, references/post-task-sync.md
