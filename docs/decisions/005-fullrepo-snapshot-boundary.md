# ADR-005: Fullrepo snapshot boundary and auditability

- Status: superseded by [ADR-008: Fullrepo complete-state snapshot](008-fullrepo-complete-state-snapshot.md)
- Date: 2026-05-17
- Deciders: @rldyourmnd
- Consulted: ChatGPT 5.5 Pro audit prompt (2026-05-17) + three deep-audit reports

## Supersession Note

ADR-005 captured the 0.11.0 split between the normal runtime branch and an
agent-only `fullrepo` orphan. Live post-task synchronization later proved that
this split conflicts with the wider rldyour-flow contract: generic flow state
expects `fullrepo` to equal the current normal-branch `HEAD` plus ignored
agent-only files. ADR-008 supersedes this decision and makes `fullrepo` a
complete portable snapshot.

## Context and Problem Statement

External auditors received a `rldyour-opencode-fullrepo.zip` archive and treated it as the complete working repository. The archive omits `opencode.json`, `VERSION`, `CHANGELOG.md`, `README.md`, `.env.example`, and `.github/workflows/` because those files are excluded from the `fullrepo` orphan branch via `scripts/fullrepo_sync.sh::AGENT_ONLY_PATTERNS`. The marketplace ships two artifact classes - normal-branch runtime and agent-only `fullrepo` snapshot - but the boundary was not documented, and local validators / docs / memories did not consistently declare which class they applied to.

The result was a structural contradiction visible to every auditor: `AGENTS.md` and `.claude/CLAUDE.md` declared `opencode.json` / `VERSION` / `CHANGELOG.md` as required source-of-truth files, while the artifact under audit (the `fullrepo` snapshot) did not contain them. Validators (`scripts/validate_config.sh`, `scripts/doctor_opencode.sh`, `scripts/tests/test_plugin_surface.py`) failed against the snapshot even when the actual code was correct.

## Decision Drivers

- Auditors and contributors must be able to verify the marketplace from a single artifact without guessing which branch they are on.
- The normal branch must remain self-sufficient for runtime verification (`opencode debug config | skill | agent build`).
- The `fullrepo` orphan branch must remain useful as portable agent-only context for AI tools that need `AGENTS.md` / `.claude/CLAUDE.md` / `.serena/memories/*` without the full repository.
- Validation scripts must be snapshot-aware: they must skip root-only checks with a deterministic `[INFO]` status when running against a fullrepo snapshot, not crash.

## Considered Options

1. Distribute only the fullrepo snapshot. Reject - runtime verification becomes impossible without `opencode.json` and CI workflows.
2. Distribute only the normal branch. Reject - the agent-only export pipeline is the point of `fullrepo`; removing it breaks the migration / handoff workflows documented in `docs/release-process.md`.
3. Distribute the normal branch as the canonical release artifact, keep `fullrepo` as an agent-only mirror, and formalise both classes in docs + validators + scripts. **Selected.**

## Decision Outcome

Two artifact classes are formally defined and validators / docs / packaging must declare which class they apply to:

| Class | What lives there | Branch | Validation surface |
|---|---|---|---|
| Normal-branch runtime | `opencode.json`, `README.md`, `VERSION`, `CHANGELOG.md`, `.env.example`, `scripts/`, `docs/`, `references/`, `.github/`, `.opencode/{agents,skills,commands,plugins}/`, `LICENSE`, governance files | `main` | full `validate_config.sh` + `pytest` + `tsc` + lint + CI workflows |
| Agent-only snapshot | `AGENTS.md`, `.claude/CLAUDE.md`, `.serena/memories/*`, `.serena/project.yml`, plus all normal-branch agent surfaces re-published into the orphan | `fullrepo` | only the agent-only contracts (`validate_instruction_docs.py`, frontmatter validators); root manifest / version / CI checks skip with `[INFO]` |

Implementation:

- `scripts/fullrepo_sync.sh` continues to copy agent-only patterns into `fullrepo` and explicitly excludes runtime markers via `RUNTIME_EXCLUDE_PATTERNS`. The exclude list now includes `.serena/.command_audit.log` to prevent runtime marker leakage.
- `CONTRIBUTING.md` documents the split as the first repository-layout section.
- Validators must catch `FileNotFoundError` on `opencode.json` and report a deterministic `[ERR] file not found` instead of an unhandled traceback (delivered as part of 0.11.0).
- New CI workflow `instruction-docs-check.yml` runs only when AGENTS.md or `.claude/CLAUDE.md` are present on the checked-out branch (path-filtered), so a normal-branch PR that does not touch those files is not penalised.

## Consequences

Positive:

- Auditors can unambiguously classify an archive as either runtime or agent-only and apply the matching validation surface.
- The defensive `RUNTIME_EXCLUDE_PATTERNS` list prevents accidental runtime-marker leakage into `fullrepo` publication.
- `instruction-docs-check.yml` and `validate_instruction_docs.py` are now safe to invoke on either branch class.

Negative:

- Release operators must remember to publish two artifacts on a tagged release (the normal branch via `release.yml` and the agent-only mirror via `fullrepo_sync.sh publish`). This is encoded in `docs/release-process.md`.
- Cross-class consistency checks (counts / pointers between `AGENTS.md` and `CHANGELOG.md`) cannot be enforced in one CI job; they live in separate workflows and `instruction-docs-sync` skill.

## Compliance

- 0.11.0 groups A-J implement the validator / docs / scripts split.
- `scripts/tests/test_validate_helpers.py::test_opencode_json_missing_file_returns_err` and `scripts/tests/test_fullrepo_sync.py::test_runtime_exclude_patterns_cover_command_audit_log` lock the contract from regression.
