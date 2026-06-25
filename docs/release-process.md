# Release Process

This repository is published as an OpenCode configuration marketplace under SemVer (`MAJOR.MINOR.PATCH`). No pre-release tags in `main`.

## When to bump

| Change class | Bump | Examples |
|---|---|---|
| Breaking removal or schema-incompatible rename | MAJOR | Removing a domain, renaming a skill, dropping an MCP server users depended on, changing required env var names |
| Backward-compatible feature | MINOR | Adding a new skill / agent / command / MCP server / plugin event handler / reference doc, expanding allowlisted bash patterns |
| Backward-compatible fix or doc-only refresh | PATCH | Fixing model IDs to match OpenCode registry, fixing schema validation drift, narrowing permissions, doc/typo fixes |

Multiple changes in one release follow the highest applicable bump. Atomic commits use Conventional Commits; the release note aggregates them per CHANGELOG section.

## Release checklist

1. `bash scripts/validate_config.sh` - exit 0.
2. `uvx --from "pytest==9.0.3" --with "pyyaml==6.0.3" --with "jsonschema==4.26.0" --with "referencing==0.36.2" pytest scripts/tests/` - all unit tests green.
3. `opencode debug config` - must resolve without error.
4. `opencode debug skill | python3 -c "import json,sys;print(len(json.load(sys.stdin)))"` - equals the `.opencode/skills/` directory count.
5. `bash scripts/check_lsps.sh` - at minimum every LSP defined in `opencode.json.lsp` must resolve to an executable.
6. `bash scripts/check_deps_freshness.sh --check-freshness` - report all pinned MCP dependencies and registry freshness.
7. `python3 scripts/check_action_pins.py .github/workflows --remote` - verify every GitHub Actions SHA pin matches its inline semver tag comment.
8. Update `CHANGELOG.md` with a new dated section; group entries under `Added` / `Changed` / `Fixed` / `Removed` per Keep a Changelog 1.1.0.
9. Update `VERSION` to the new SemVer.
10. Update `README.md` if catalog counts changed (skills / commands / MCP / plugins / scripts / tests).
11. `git commit` with subject `chore(release): X.Y.Z` and the CHANGELOG block in the body.
12. `git tag X.Y.Z` (annotated, signed if configured).
13. Push `main` and tags; public repositories use automatic CI/CD by default. Verify the GitHub Actions runs for the pushed HEAD/tag, including `.github/workflows/validate.yml` (which runs both `validate_config.sh` and `pytest scripts/tests/`). If a required release/readiness workflow did not run because it is dispatch-only, scheduled, or release-only, trigger that existing workflow with `gh workflow run` and wait for it.

## Tracked agent context

Durable agent context (`AGENTS.md`, `.serena/project.yml`,
`.serena/memories/*`, `.serena/plans/`, `.serena/research/`,
`.serena/newproj/`, and `.serena/deploy/`) is committed on `main` with the
source change that makes its facts true. Runtime markers, cache, review scratch
files, diagnostics, local env files, browser artifacts, tokens, cookies, and
credentials must remain ignored.

## Hotfix branch (when `main` is locked)

1. Branch from the previous release tag: `git checkout -b hotfix/X.Y.Z+1 X.Y.Z`.
2. Apply the fix atomically.
3. Bump PATCH, update CHANGELOG, validate as above.
4. Open a PR back into `main`; tag after merge.

## What never enters a release

- Real API keys, tokens, cookies, or local credentials in any tracked file.
- Hard-coded absolute paths under `/Users/<owner>/...` outside test fixtures.
- Runtime markers under `.serena/.*sync*`, `.serena/.flow_*`, `.serena/.dirty_stop_ack`.
- Browser-generated artifacts (`browser/`, screenshots).
- `.opencode/node_modules/` or any Bun runtime cache.
