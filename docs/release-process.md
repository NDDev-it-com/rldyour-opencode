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

1. `bash scripts/validate_config.sh` — exit 0.
2. `opencode debug config` — must resolve without error.
3. `opencode debug skill | python3 -c "import json,sys;print(len(json.load(sys.stdin)))"` — equals the `.opencode/skills/` directory count.
4. `bash scripts/check_lsps.sh` — at minimum every LSP defined in `opencode.json.lsp` must resolve to an executable.
5. Update `CHANGELOG.md` with a new dated section; group entries under `Added` / `Changed` / `Fixed` / `Removed` per Keep a Changelog 1.1.0.
6. Update `VERSION` to the new SemVer.
7. Update `README.md` if catalog counts changed (skills / commands / MCP / plugins).
8. `git commit` with subject `chore(release): X.Y.Z` and the CHANGELOG block in the body.
9. `git tag vX.Y.Z` (annotated, signed if configured).
10. Push `main` and tags; CI (`.github/workflows/validate.yml`) must stay green.

## Publishing agent-only context

After the release commit lands on `main`, run:

```bash
bash scripts/fullrepo_sync.sh publish
```

This force-with-lease pushes the agent-only snapshot to `origin/fullrepo`, stripping runtime markers (`.serena/cache/`, `.opencode/node_modules/`, etc.) and aborting if any secret pattern is detected.

## Hotfix branch (when `main` is locked)

1. Branch from the previous release tag: `git checkout -b hotfix/X.Y.Z+1 vX.Y.Z`.
2. Apply the fix atomically.
3. Bump PATCH, update CHANGELOG, validate as above.
4. Open a PR back into `main`; tag after merge.

## What never enters a release

- Real API keys, tokens, cookies, or local credentials in any tracked file.
- Hard-coded absolute paths under `/Users/<owner>/…` outside test fixtures.
- Runtime markers under `.serena/.*sync*`, `.serena/.flow_*`, `.serena/.dirty_stop_ack`.
- Browser-generated artifacts (`browser/`, screenshots).
- `.opencode/node_modules/` or any Bun runtime cache.
