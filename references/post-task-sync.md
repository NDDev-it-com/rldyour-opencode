# Post-Task Synchronization

Post-task sync is the last phase of meaningful work. It prevents forgotten changes, stale project knowledge, and mismatched local/GitHub/server state.

## Order

1. Serena memory freshness first.
2. Project instruction docs second: `AGENTS.md` and `.opencode/` configuration.
3. Quality checks and manual evidence third.
4. Atomic commits fourth.
5. GitHub sync fifth.
6. Repository context check sixth.
7. Merged branch/worktree cleanup last.

For public repositories, GitHub sync includes verifying the GitHub Actions runs
for the pushed HEAD/tag. If an existing readiness or release workflow is
dispatch-only, scheduled, or release-only and did not run automatically for the
public-repo change, trigger it with `gh workflow run` and wait for completion.
Private repositories keep the manual trigger default.

## Session And Commit Advice

OpenCode loads instruction docs at session start. Treat this context as an input to planning: inspect dirty files, ahead/behind state, worktree count, docs, and Serena freshness before making assumptions.

## Serena Interaction

Serena MCP owns `.serena/memories`, `.serena/plans`, and `.serena/research`. The sync workflow waits until Serena state is current, then runs memory synchronization through `@flow-memory-sync`.

Serena knowledge is tracked on main when it is durable; runtime-local state stays ignored.

## AGENTS.md And OpenCode Configuration

`AGENTS.md` is the cross-tool root project-instruction file (see https://agents.md/). Update it when the task changes durable project rules, setup commands, quality gates, deploy contracts, architecture constraints, or agent workflow guidance. Keep it concise and practical: repository layout, commands, checks, constraints, tool routing, and done criteria.

OpenCode reads project configuration from `opencode.json` and agent/skill/command definitions from `.opencode/`. Update these when the task changes agent definitions, skill configurations, or command templates.

Both AGENTS.md and opencode.json must contain verified facts, not chat history or speculative plans.

Durable AI workflow files such as `AGENTS.md`, `.serena/memories/`, `.serena/project.yml`, and `.opencode/` are tracked on main. Runtime-local cache, diagnostics, review scratch files, markers, local env files, browser artifacts, and secrets stay ignored.

## Repository Context

Durable repository context is part of the normal tracked tree. Use ordinary git review, commits, tags, releases, and reverts for context changes.

## Commit Rules

- Commit source changes by logical feature/fix/refactor units.
- Commit Serena/docs sync separately when it improves history clarity.
- Never commit secrets, runtime markers, browser artifacts, local env files, or accidental generated junk.
- Use Conventional Commits.
- Push to upstream when configured. If upstream is missing, ask before setting it.

## Cleanup Rules

- Remove merged worktrees and branches only after verifying they are merged into `main` and pushed if needed.
- Delete remote branches after merge only when policy allows it, the branch was created for this workflow, and no open PR depends on it. Protected branches such as `main` are never cleanup candidates.
- Ask the user if branch ownership, merge status, or remote state is unclear.
