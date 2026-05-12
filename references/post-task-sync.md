# Post-Task Synchronization

Post-task sync is the last phase of meaningful work. It prevents forgotten changes, stale project knowledge, and mismatched local/GitHub/server state.

## Order

1. Serena memory freshness first.
2. Project instruction docs second: `AGENTS.md` and `.opencode/` configuration.
3. Quality checks and manual evidence third.
4. Atomic commits fourth.
5. GitHub sync fifth.
6. Fullrepo branch sync sixth.
7. Merged branch/worktree cleanup last.

## Session And Commit Advice

OpenCode loads instruction docs at session start. Treat this context as an input to planning: inspect dirty files, ahead/behind state, worktree count, docs, and Serena freshness before making assumptions.

## Serena Interaction

Serena MCP owns `.serena/memories`, `.serena/plans`, and `.serena/research`. The sync workflow waits until Serena state is current, then runs memory synchronization through `@flow-memory-sync`.

In fullrepo-managed projects, Serena knowledge is not committed to normal branches. The fullrepo publish step handles the complete snapshot.

## AGENTS.md And OpenCode Configuration

`AGENTS.md` is the cross-tool root project-instruction file (see https://agents.md/). Update it when the task changes durable project rules, setup commands, quality gates, deploy contracts, architecture constraints, or agent workflow guidance. Keep it concise and practical: repository layout, commands, checks, constraints, tool routing, and done criteria.

OpenCode reads project configuration from `opencode.json` and agent/skill/command definitions from `.opencode/`. Update these when the task changes agent definitions, skill configurations, or command templates.

Both AGENTS.md and opencode.json must contain verified facts, not chat history or speculative plans.

For normal projects, root `AGENTS.md`, `.serena/`, `.opencode/` agents/skills/commands, and similar AI workflow files are agent-only files. They should be excluded from normal branch history through `.git/info/exclude` and published to the `fullrepo` branch.

## Fullrepo Branch

`fullrepo` is the portable complete-state branch. It lets a new machine initialize with the same agent-only project context while keeping `main` and feature branches free of AI workflow files.

Post-task flow:

1. Commit and push normal source/test/docs/config changes to the current upstream branch.
2. Ensure `.git/info/exclude` has the rldyour fullrepo block.
3. Publish agent-only files to the `fullrepo` branch after the normal branch is at its final `HEAD`.
4. Verify branch refs before final delivery.

Initialization flow:

1. Before relying on missing agent-only context, check `origin/fullrepo`.
2. If `origin/fullrepo` exists, restore its agent-only files and install excludes.
3. If `origin/fullrepo` does not exist but local agent-only files exist, publish the initial `fullrepo` snapshot.
4. If the current branch tracks agent-only files, remove them from the index and commit that cleanup on the normal branch before final delivery.

`fullrepo` uses safe force updates because it is a generated snapshot branch. Use `--force-with-lease`, not a blind `--force`, so an unexpected remote update cannot be silently overwritten.

## Commit Rules

- Commit source changes by logical feature/fix/refactor units.
- Commit Serena/docs sync separately when it improves history clarity.
- Never commit secrets, runtime markers, browser artifacts, local env files, or accidental generated junk.
- Use Conventional Commits.
- Push to upstream when configured. If upstream is missing, ask before setting it.

## Cleanup Rules

- Remove merged worktrees and branches only after verifying they are merged into `main` and pushed if needed.
- Delete remote branches after merge when the branch was created for this workflow and no open PR depends on it. Protected branches such as `main` and `fullrepo` are never cleanup candidates.
- Ask the user if branch ownership, merge status, or remote state is unclear.
