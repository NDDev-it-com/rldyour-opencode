# Rollback And Restore

Rollback paths for a marketplace project are simpler than for a production service — there is no live data, but a broken `opencode.json` or agent definition takes the owner's workflow offline. This doc captures the safe restore order.

## Local working-tree rollback

When a local edit broke `opencode debug config`:

1. Reproduce the error: `opencode debug config 2>&1 | head -20`. The first `Error: Configuration is invalid at …` line points to the offending file and field.
2. `git diff` the named file. If the diff is small and obviously wrong, `git restore <file>`.
3. If multiple files contributed, revert the latest commit:
   ```bash
   git revert HEAD --no-edit
   ```
   Conventional Commits make `git log --oneline -10` enough to find the right SHA.
4. Re-validate: `bash scripts/validate_config.sh && opencode debug config >/dev/null`.

Never `git reset --hard` on `main` to undo a bad change — use `git revert` so the history records the rollback.

## Restoring agent-only files

If `.serena/`, `.opencode/agents`, `.opencode/skills`, `.opencode/commands`, `.opencode/plugins`, or `AGENTS.md` are missing locally:

```bash
bash scripts/fullrepo_sync.sh bootstrap-init
```

`bootstrap-init` installs the `.git/info/exclude` rldyour block and restores from `origin/fullrepo`. If `origin/fullrepo` does not exist yet, run `bash scripts/fullrepo_sync.sh publish` from a known-good clone first.

## Restoring a published release

To roll a release back when consumers report regressions:

1. `git tag -d vX.Y.Z` locally if the tag was unpushed; `git push --delete origin vX.Y.Z` only with explicit owner approval.
2. Open a hotfix branch from the previous good tag (`docs/release-process.md` §Hotfix branch).
3. Land the fix, bump PATCH, run release checklist.
4. Communicate the rollback in the new CHANGELOG section (`### Fixed` entry that names the regression).

Never amend or force-push an existing release tag. Make a new patch release instead.

## Restoring Serena memories

If `.serena/memories/` is corrupted, partially deleted, or contains stale claims that fail to verify against current code:

1. Run `bash scripts/fullrepo_sync.sh restore` to pull the last published memory snapshot from `origin/fullrepo`.
2. Re-run the `serena-memory-sync` skill (or `@flow-memory-sync` subagent) to refresh memories against the current HEAD.
3. Commit the refresh as `chore(serena): sync project knowledge after <HEAD-SHA>`.

The memory sync workflow rejects auto-commit when non-knowledge files have uncommitted changes, so resolve those first (`git restore` or commit them) before retrying.

## What rollback does NOT cover

- Anthropic provider auth (`auth.json` under `~/.local/share/opencode/`) — re-run `opencode providers` (alias `opencode auth`) and re-authenticate.
- MCP server runtime caches — they regenerate on next start; never restore from another machine.
- Bun's `.opencode/node_modules/` — regenerated automatically; do not commit or restore.
