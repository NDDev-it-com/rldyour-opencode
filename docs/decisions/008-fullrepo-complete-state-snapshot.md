# ADR-008: Fullrepo complete-state snapshot

- Status: accepted
- Date: 2026-05-18
- Deciders: @rldyourmnd
- Supersedes: [ADR-005](005-fullrepo-snapshot-boundary.md)

## Context and Problem Statement

ADR-005 made `fullrepo` an agent-only orphan branch. That solved one audit
problem by documenting why `opencode.json`, `VERSION`, `CHANGELOG.md`,
`.github/workflows/`, and other runtime files were missing from the snapshot,
but it left a deeper integration problem:

- auditors still could not validate the marketplace from the `fullrepo`
  artifact alone;
- generic `rldyour-flow` post-task state computes the expected `fullrepo` tree
  as current normal-branch `HEAD` plus ignored agent-only files;
- the repo-local `scripts/fullrepo_sync.sh` published only selected paths, so
  generic flow state repeatedly reported `fullrepo_needs_attention: true` even
  after repo-local `/ry-sync` was complete.

The result was a Stop-hook loop for a genuinely synchronized repository.

## Decision Drivers

- `fullrepo` must be portable enough for a fresh machine or AI agent to restore
  the complete project context without guessing which branch supplies runtime
  files.
- The normal branch remains the canonical product/runtime branch and must keep
  agent-only files out of its tracked history.
- Runtime markers, local caches, secrets, diagnostics, and browser artifacts
  must never enter either `main` or `fullrepo`.
- Repo-local sync commands must agree with generic rldyour-flow state checks so
  post-task sync can terminate deterministically.

## Considered Options

1. Keep ADR-005 and special-case `rldyour-opencode` in the generic hook.
   Reject — it preserves a project-specific exception and makes future flow
   tooling harder to reason about.
2. Keep `fullrepo` agent-only and leave `.flow_sync_marker` as a loop guard.
   Reject — this acknowledges the loop but does not fix the state mismatch.
3. Publish `fullrepo` as current `HEAD` plus ignored agent-only context, while
   still excluding runtime markers and secrets. **Selected.**

## Decision Outcome

`fullrepo` is now a complete-state generated branch:

| Branch | Contents | Validation surface |
|---|---|---|
| `main` | Product/runtime files only: `opencode.json`, `.opencode/`, `scripts/`, docs, references, governance, workflows, release files | Full local + CI gates |
| `fullrepo` | Exact current `main` tree plus ignored agent-only files: `AGENTS.md`, `.claude/CLAUDE.md`, `.serena/memories/*`, `.serena/project.yml`, and similar project knowledge | Full local + CI gates can run after checkout; instruction-doc gates can also validate agent-only files |

Implementation:

- `scripts/fullrepo_sync.sh publish` starts from `HEAD`, overlays agent-only
  files from the working tree, strips `RUNTIME_EXCLUDE_PATTERNS`, scans for
  secret-looking values, writes a tree, and pushes `origin/fullrepo` with
  `--force-with-lease`.
- `scripts/fullrepo_sync.sh status-json` reports whether local and remote
  `fullrepo` trees match the expected `HEAD + agent-only` tree.
- `scripts/fullrepo_sync.sh restore` remains agent-only: it restores only the
  ignored project knowledge files from `origin/fullrepo` into the normal
  checkout.

## Consequences

Positive:

- `fullrepo` no longer omits runtime manifests, CI workflows, or release files.
- Generic rldyour-flow state and repo-local sync state agree on the expected
  tree, so completed post-task sync does not loop.
- Auditors can validate a `fullrepo` archive without classifying it as a
  reduced artifact first.

Negative:

- The generated branch is larger because it contains the whole normal branch
  tree in addition to agent-only context.
- `fullrepo` publication must refuse dirty non-runtime files; otherwise the
  generated branch would not correspond to a committed `HEAD`.

## Compliance

- `scripts/tests/test_fullrepo_sync.py::test_publish_creates_complete_head_plus_agent_snapshot`
  proves that `fullrepo` contains root runtime files plus agent-only files and
  excludes runtime markers.
- `scripts/tests/test_fullrepo_sync.py::test_status_json_field_types` covers the
  new tree-match status fields.
