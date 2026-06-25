---
name: flow-post-task-sync
description: "Финализация задачи: Serena memories, tracked agent context, git/GitHub, ветки. Используй для: заверши задачу, синхронизируй, sync and finalize, заверши работу. EN triggers: finalize task, post-task sync, memory sync, finalize before delivery."
---

# Flow Post-Task Sync

## Purpose

Leave the project in a synchronized, documented, committed state. This skill runs after Serena memory sync, not instead of it.

## Workflow

1. Confirm Serena memories are current. If stale, run `serena-memory-sync` first.
2. If flow state reports `execution.agent_role=worker`, do not run global sync. Return the worker JSON report to the orchestrator. Workers must not delete branches, push, install system configs, mutate project policy, or run final sync unless the orchestrator explicitly delegated that exact action.
3. Inspect flow state markers (`.serena/.flow_post_task_state.json`, `.serena/.flow_sync_marker`) if present. Run git sync audit when branch/worktree cleanup is not obviously complete.
4. Inspect uncommitted changes deeply. Separate source changes, docs, Serena knowledge, generated junk, runtime markers, and secrets.
5. Run `instruction-docs-sync` when durable project instructions may have changed. Keep `AGENTS.md` optimized for the current agent environment.
6. Run applicable quality checks from project scripts and detected stack checks.
7. Commit atomically with Conventional Commits. Use separate commits for
   implementation, tests/validators, docs/instructions, license/metadata,
   generated artifacts, and Serena memory sync when that improves history
   clarity or reviewability.
8. Push to upstream when configured. If no upstream exists, ask before creating one.
9. Follow the effective `.rldyour/project-policy.json` / local / env policy before touching agent files. Tracked AI instruction files and durable Serena memories are normal project files; runtime-local cache, diagnostics, markers, browser artifacts, and secrets remain forbidden.
10. Remove merged local and remote branches/worktrees only when policy allows cleanup, the branch is not protected (`main`, `dev`, etc.), the branch was created for this workflow, and no open PR depends on it. Advisory cleanup is reported, not forced.
11. Remove `.serena/.flow_sync_marker`, `.serena/.flow_post_task_state.json`, and `.serena/.flow_blocker_ack.json` only after flow state reports no policy-allowed blocking reasons.

## Loop Guard

Do not edit runtime marker files except to remove them after sync. If a sync hook repeats for the same fingerprint, report the blocker instead of forcing new commits. The guard prevents infinite commit-sync cycles:

- If the same set of files is committed and synced more than twice with no logical change, stop and report.
- If a marker file keeps reappearing after removal, investigate the source instead of removing again.
- If a pre-commit hook modifies files that trigger another sync, resolve the hook output before committing.

## Repository Context

Durable AI context is tracked on `main`: `AGENTS.md`, `.opencode/`,
`.serena/project.yml`, and `.serena/memories/`. Runtime markers, caches, local
env files, browser artifacts, diagnostics, review scratch files, and secrets
remain ignored.

## Output

Report in Russian:

- Serena memories status (current / synced / stale).
- Uncommitted changes summary by category.
- Commits made (type, scope, message).
- Push status.
- Branch/worktree cleanup actions.
- Repository context status.
- Final project state.
