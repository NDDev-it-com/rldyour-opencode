# Pull Request

## Summary

<!-- One paragraph: what does this PR change and why. -->

## Scope

- [ ] Code (`.opencode/plugins/`, `.opencode/agents/`, `.opencode/skills/`, `.opencode/commands/`)
- [ ] Configuration (`opencode.json`, `.opencode/package.json`, `.opencode/tsconfig.json`)
- [ ] Scripts / validators (`scripts/`, `scripts/tests/`)
- [ ] Documentation (`AGENTS.md`, `README.md`, `references/`, `docs/`)
- [ ] Architecture decision (`docs/decisions/NNN-slug.md`)
- [ ] CI / governance (`.github/workflows/`, `.github/CODEOWNERS`, dependabot)
- [ ] Serena memories (`.serena/memories/`)
- [ ] Versioning / release (`VERSION`, `CHANGELOG.md`)

## Validation evidence

All gates relevant to the touched surface must run green locally. Tick what you ran:

- [ ] `bash scripts/validate_config.sh` — opencode.json + frontmatter + VERSION
- [ ] `uvx --from "pytest==9.0.2" --with "pyyaml==6.0.3" pytest scripts/tests/` — full suite
- [ ] `bash scripts/check_deps_freshness.sh` — pin report
- [ ] `bash scripts/check_deps_freshness.sh --check-freshness` — network freshness (if dependency change)
- [ ] `bunx --bun tsc --noEmit -p .opencode/tsconfig.json` — plugin typecheck (if plugin change)
- [ ] `ruff check scripts` — python lint (if scripts change)
- [ ] `opencode debug config / skill / agent build` — runtime resolve (if config change)
- [ ] `python3 scripts/smoke_mcp_capabilities.py` — MCP reachability (if MCP change)

## Risk assessment

- Reversibility: <!-- easy / requires migration / destructive -->
- Blast radius: <!-- one file / one domain / cross-cutting -->
- Backwards compatibility: <!-- yes / no / N/A -->
- Security impact: <!-- none / hardening / surface change -->

## ADR / context

<!-- Link the ADR if this PR encodes an architectural decision.
Link previous discussion (issue, audit, /ry-review report) if relevant. -->

## Checklist

- [ ] Conventional Commits format on every commit (`type(scope): description`, ≤72 chars)
- [ ] Atomic commits (one logical change per commit)
- [ ] No `--amend` of pushed commits
- [ ] No hacks, fake green checks, or untracked debt
- [ ] No secrets in commits, logs, docs, or memories
- [ ] Domain boundaries respected (one domain per skill / agent / command)
- [ ] Touched docs synchronized (counts, pointers, ADR banners, memory cross-refs)
- [ ] `/ry-sync` planned before final delivery
