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
8. Keep normal branch history clean from agent-only files. Ensure `.git/info/exclude` contains the rldyour fullrepo block and move tracked agent-only files out of the current branch only when the project is ready for that migration.
9. Publish the complete project snapshot to `fullrepo` through sync scripts. This uses safe `--force-with-lease`, not a blind force push.
10. Remove merged local and remote branches/worktrees only after verifying they are merged into `main` and no open PR depends on them. Leave protected branches such as `main` and `fullrepo`; report any ambiguous branch ownership instead of deleting silently.
11. Remove `.serena/.flow_sync_marker` and `.serena/.flow_post_task_state.json` after successful sync.

## Loop Guard

Do not edit runtime marker files except to remove them after sync. If a sync hook repeats for the same fingerprint, report the blocker instead of forcing new commits. The guard prevents infinite commit-sync cycles:

- If the same set of files is committed and synced more than twice with no logical change, stop and report.
- If a marker file keeps reappearing after removal, investigate the source instead of removing again.
- If a pre-commit hook modifies files that trigger another sync, resolve the hook output before committing.

## Fullrepo Branch

`fullrepo` is the portable AI-context branch. It contains the normal branch tree plus agent-only files such as project `AGENTS.md`, `.serena` knowledge, `.opencode/` agents/skills/commands, `.claude`, `.cursor/rules`, `.agents/skills`, and similar agent workflow files. The main branch should not track those files in normal projects; they should be restored locally from `fullrepo` and ignored through `.git/info/exclude`.

### Fullrepo Workflow

1. **Bootstrap** (`--bootstrap-init`): restore agent-only files from `fullrepo` to local working tree if `fullrepo` exists; publish local agent-only files to `fullrepo` if it does not exist.
2. **Migrate** (`--migrate-main`): remove tracked agent-only files from `main` branch index after they are published to `fullrepo`. Add them to `.git/info/exclude`.
3. **Publish** (`--publish`): sync current agent-only files to `fullrepo` branch. Uses `--force-with-lease` for safety.
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
