---
name: flow-post-task-sync
description: "Финализация задачи: Serena memories, agent-only файлы, fullrepo, git/GitHub, ветки. Используй для: заверши задачу, синхронизируй, sync and finalize, заверши работу. EN triggers: finalize task, post-task sync, memory sync, sync to fullrepo, finalize before delivery."
---

# Flow Post-Task Sync

## Purpose

Leave the project in a synchronized, documented, committed state. This skill runs after Serena memory sync, not instead of it.

## Workflow

1. Confirm Serena memories are current. If stale, run `serena-memory-sync` first.
2. Inspect flow state markers (`.serena/.flow_post_task_state.json`, `.serena/.flow_sync_marker`) if present. Run git sync audit when branch/worktree cleanup is not obviously complete.
3. Inspect uncommitted changes deeply. Separate source changes, docs, Serena knowledge, generated junk, runtime markers, and secrets.
4. Run `instruction-docs-sync` when durable project instructions may have changed. Keep `AGENTS.md` optimized for the current agent environment.
5. Run applicable quality checks from project scripts and detected stack checks.
6. Commit atomically with Conventional Commits. Use separate commits for
   implementation, tests/validators, docs/instructions, license/metadata,
   generated artifacts, and Serena/fullrepo sync when that improves history
   clarity or reviewability.
7. Push to upstream when configured. If no upstream exists, ask before creating one.
8. Follow the effective `.rldyour/project-policy.json` / local / env policy before touching fullrepo or agent files. In `fullrepo.mode=disabled`, do not restore, migrate, publish, create, or install fullrepo excludes. In `normal_branch_policy.agent_files=allowed`, tracked AI instruction files are normal project files.
9. Publish `fullrepo` only when policy requires/allows it through sync scripts. Missing fullrepo creation requires explicit policy (`create_if_missing=true`) or explicit current user instruction.
10. Remove merged local and remote branches/worktrees only when policy allows cleanup, the branch is not protected (`main`, `dev`, `fullrepo`, etc.), the branch was created for this workflow, and no open PR depends on it. Advisory cleanup is reported, not forced.
11. Remove `.serena/.flow_sync_marker`, `.serena/.flow_post_task_state.json`, and `.serena/.flow_blocker_ack.json` only after flow state reports no policy-allowed blocking reasons.

## Loop Guard

Do not edit runtime marker files except to remove them after sync. If a sync hook repeats for the same fingerprint, report the blocker instead of forcing new commits. The guard prevents infinite commit-sync cycles:

- If the same set of files is committed and synced more than twice with no logical change, stop and report.
- If a marker file keeps reappearing after removal, investigate the source instead of removing again.
- If a pre-commit hook modifies files that trigger another sync, resolve the hook output before committing.

## Fullrepo Branch

`fullrepo` is the default portable AI-context branch for rldyour-managed projects. Project policy may set `fullrepo.mode=disabled|advisory|auto|required` and may allow tracked instruction/AI files in normal branches. Runtime markers, caches, local env files, browser artifacts, and secrets remain forbidden in every mode.

### Fullrepo Workflow

1. **Bootstrap** (`bootstrap-init`): restore agent-only files from `fullrepo` only when policy allows it. Creating missing fullrepo requires `fullrepo.create_if_missing=true` or explicit current user instruction.
2. **Migrate**: remove tracked agent-only files from `main` only when project policy says they should be fullrepo-managed.
3. **Publish** (`publish`): sync current agent-only files to `fullrepo` only when policy allows it. Uses `--force-with-lease` for safety.
4. **Verify**: after publish, confirm `fullrepo` contains the expected files and `main` does not track agent-only files.

## Output

Report in Russian:

- Serena memories status (current / synced / stale).
- Uncommitted changes summary by category.
- Commits made (type, scope, message).
- Push status.
- Branch/worktree cleanup actions.
- Fullrepo publish status.
- Final project state.
