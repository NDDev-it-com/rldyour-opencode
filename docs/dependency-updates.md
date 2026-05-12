# Dependency Updates

This repository pins exact versions for every external dependency to keep startup reproducible across machines. The owner's policy is latest-compatible-stable: prefer the newest release where (a) the upstream changelog has no known regression flagged within the last two minor versions, and (b) the API surface used here is unchanged.

## Pinned surfaces

| Where | What | How to bump |
|---|---|---|
| `opencode.json` → `mcp.<name>.command` | npm packages (`@modelcontextprotocol/server-sequential-thinking`, `@playwright/mcp`, `chrome-devtools-mcp`, `shadcn`) | check npm view, update version, restart OpenCode, verify `opencode debug config` |
| `opencode.json` → `mcp.<name>.command` | Python tools via `uvx` (`serena-agent`, `semgrep`) | check PyPI, update pinned version, verify MCP startup |
| `opencode.json` → `mcp.<name>.command` | Dart SDK (`dart mcp-server`) | follow Dart SDK stable channel |
| `.opencode/package.json` | `@opencode-ai/plugin` | OpenCode auto-pins to its own runtime version on `bun install`; do not change manually unless intentionally diverging |
| `opencode.json` → `model` / `small_model` | Anthropic model IDs | run `opencode models anthropic` for the authoritative list before changing |
| `opencode.json` → `lsp.<key>.command` | language servers (ruff, marksman, taplo, …) | follow `references/lsp-server-matrix.md`; check brew/`pipx` before bumping |

## Workflow

1. Identify a candidate bump (changelog, release feed, security advisory).
2. Cross-reference the source of truth (`mcp.<name>.command`, `lsp.<key>.command`, `model`).
3. Read the upstream changelog for the new version; flag breaking changes explicitly.
4. Edit the pin in `opencode.json` (or `.opencode/package.json` if intentional override is needed).
5. Restart OpenCode (or run `opencode debug config`) and confirm:
   - config resolves without error;
   - the new MCP/LSP starts (`opencode debug info`, MCP listing not empty);
   - touched skills/agents still invoke the server.
6. Commit with `chore(deps): bump <name> X.Y → X'.Y'` and reference the release notes in the body.
7. If the bump is non-trivial (semantic change, new env var required, replaced binary), update `AGENTS.md` and the relevant reference doc (`references/lsp-server-matrix.md`, etc.) in the same commit.

## Supply-chain rules

- Always pin to an exact version (`==X.Y.Z`, `@X.Y.Z`, `==X.Y.Z`); never use loose ranges like `^X` or `latest`.
- Prefer `bunx` for npm packages and `uvx` for Python — both run isolated, both verify the package source before execution.
- Reject any package whose maintainer list, license, or homepage cannot be verified against `references/sources.md` policy.
- Never silently downgrade a tool that another skill depends on; raise it through ADR (MADR 4.0.0) when affected.

## Automation surface

`scripts/check_deps_freshness.sh` (with helper `scripts/_extract_pins.py`) parses every pinned MCP server in `opencode.json` and lists the package + version. JSON output via `--json` is suitable for downstream automation. Network-backed comparison against npm / PyPI registries is not yet wired (intentional defer — local list is the primary value).
