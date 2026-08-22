# AGENTS.md

## Project Purpose

This is the OpenCode adapter instruction overlay for `rldyour-opencode`.
It is a system file tracked on `main` so that `install_system_opencode.sh`
copies it to the OpenCode config root on a fresh `git clone`, without
relying on an overlay restore step.

Canonical public description: rldyour AI CLI configuration for OpenCode: local plugins, MCP/LSP, permissions, commands, agents, browser/design workflows, and security review.

The file is the OpenCode install surface for the owner-defined project
memory. It must remain subordinate to checked source files: `opencode.json`,
`.opencode/**`, `references/**`, scripts, tests, and the root control-plane
tuple.

## Source Of Truth

- Repository: `NDDev-it-com/rldyour-opencode`
- Branch: `main`

The durable source of truth is the current code/config/tests/git state, not a
value copied into this overlay:

- `opencode.json`
- `.opencode/**`
- `references/**` - `references/opencode-baseline.json` is the single pin for the
  OpenCode runtime/plugin/SDK/schema baseline (`opencode-ai`,
  `@opencode-ai/plugin`, and `@opencode-ai/sdk`).
- `scripts/**`
- `tests/**`
- root `config/repositories.json` - owns the adapter product version
  (`product_version`) and the control-plane pinned commit (`expected_head`).

Do not duplicate the product version, pinned commit, or runtime version as
standalone literals in this file; read them from the files above so they cannot
drift. This overlay is derived context only.

## Domain Boundaries

Use OpenCode-native surfaces only:

- `opencode.json`
- `.opencode/skills/*/SKILL.md`
- `.opencode/commands/*.md`
- `.opencode/agents/*.md`
- `.opencode/plugins/*.ts`
- `references/rldyour-contract.json`

Do not copy Claude Code plugin formats, Codex plugin formats, or Gemini
`.gemini` formats into this adapter.

## OpenCode Conventions

When translating shared rldyour policy into OpenCode, use OpenCode-native
concepts:

- skills live under `.opencode/skills`;
- slash commands live under `.opencode/commands`;
- agents live under `.opencode/agents`;
- local plugins live under `.opencode/plugins`;
- permission behavior is encoded in `opencode.json` and release-safe overlays;
- runtime/package baselines are recorded in `references/opencode-baseline.json`.

Do not describe Codex managed agents, Claude Code hooks, or Gemini TOML command
files as active OpenCode surfaces. Comparative notes are acceptable only when
they make a boundary explicit.

## System Install Contract

`scripts/install_system_opencode.sh` installs source config from the normal
branch and copies this file directly, because `AGENTS.md` is tracked on `main`
and is present on a fresh `git clone`.

The installer-required normal source paths are:

- `opencode.json`
- `.opencode/`
- `AGENTS.md`

`AGENTS.md` is a tracked-on-main system instruction file. Durable `.serena/`
agent context (`.serena/project.yml`, `.serena/memories/`, `.serena/plans/`,
`.serena/research/`, `.serena/newproj/`, and `.serena/deploy/`) is also normal
source. Runtime-local cache, reviews, diagnostics, markers, local env files,
browser artifacts, tokens, cookies, and credentials stay ignored. The installer
still tolerates a malformed checkout missing this file by emitting an explicit
warning, but a normal clone always carries it.

The system convergence path is owned by root `/ry-repair`:

- preflight source paths before long installer phases;
- run OpenCode installer and doctor scripts with explicit timeouts;
- validate installed surfaces through positive inventories;
- validate every discovered `opencode` binary on `PATH` against the runtime
  baseline, not only the first active binary.

## Browser And Orchestration Boundary

Browser routing remains shared across the control plane:

- Before every browser action, run exact
  `$HOME/.local/bin/cloakbrowser-cdp-health`; missing or nonzero health stops as
  `NOT_PROVEN`.
- Execute only exact `$HOME/.local/bin/playwright-cli` or the exact managed
  Chrome DevTools MCP transport from `opencode.json`.
- `webwright-task` is compatibility routing only. The Webwright runtime and
  every stock/raw/in-app, package-runner, alternate-CDP, or fallback path are
  forbidden.

OpenCode agents are not cmux orchestrators. cmux orchestrator mode exists only
as one visible cmux terminal controlling visible worker terminals.

In standard mode, no software orchestrator exists. The owner operates directly
through OpenCode, Claude Code, Codex, or Antigravity CLI. In cmux orchestrator mode,
OpenCode can run as a visible worker terminal, but it must not spawn hidden
background orchestrators, daemon supervisors, or unbounded worker jobs.

OpenCode reviewer agents may analyze and report. They must not push, delete
branches, run system installs, or mutate global policy unless
the visible orchestrator explicitly delegates that exact action and project
policy permits it.

## Security And Permissions

Owner-standard OpenCode configuration intentionally allows broad primary
owner-context permissions for a trusted workstation. That posture is explicit,
not accidental. Keep these boundaries:

- primary owner contexts may allow `read`, `edit`, `bash`, `task`,
  `external_directory`, and `doom_loop` according to `opencode.json` policy;
- reviewer agents stay stricter by role;
- release-safe config remains available as a conservative artifact;
- secrets, OAuth tokens, API keys, browser profiles, local caches, and runtime
  markers must not be committed;
- permission observability belongs in OpenCode-native event hooks and plugins,
  not undocumented policy shims.

If a change weakens a guardrail, add a validator or a release note entry. Do
not rely on prose alone for security-sensitive behavior.

## MCP And Provider Inventory

Active MCP servers are governed by the root positive inventory and adapter
OpenCode config. Configure only providers listed in the approved active
inventory. Removed or historical tools must not be reintroduced unless the
owner updates the inventory and release policy.

Browser provider roles are fixed:

- Exact `$HOME/.local/bin/playwright-cli` handles health-gated browser flow and
  UI evidence. `run-code` and `--filename` are forbidden.
- The configured exact managed Chrome DevTools MCP wrapper handles health-gated
  console, network, runtime, layout, performance, memory, and Lighthouse.
- `webwright-task` preserves the old route name but runs only through these
  managed providers; it never installs or executes Webwright Python code.

Do not introduce another browser-control provider or any fallback.

## Release And Tracked Context Policy

OpenCode adapter releases are numeric-tagged. The current exact tag is `1.7.25`
(the active `product_version` in root `config/repositories.json`); older tags are
historical unless the root tuple explicitly pins them.

Before the root control plane advances the OpenCode gitlink:

1. Commit OpenCode-owned changes in this repository.
2. Push the signed release commit to `main` and wait for all exact-SHA branch
   workflows to succeed.
3. Only then create and push the immutable numeric tag.
4. Ensure durable `.serena/` context is tracked on `main` and runtime-local
   state is ignored.
5. Update the root `config/repositories.json` expected head and version.
6. Run root tuple, contract, instruction parity, repository-context, and release gates.

This file is tracked on `main`. Update it
when the OpenCode install contract, runtime baseline, browser routing,
permissions, or durable workflow rules change. Read the product version, pinned
commit, and runtime version from their source files rather than restating them
here.

## Validation Commands

Run these checks after changing OpenCode-owned source:

```bash
bash scripts/validate_config.sh
python3 scripts/validate_contract.py
python3 scripts/validate_opencode_baseline.py
python3 scripts/validate_opencode_schema.py
python3 scripts/check_baseline_consistency.py
python3 scripts/validate_instruction_docs.py
python3 scripts/validate_mcp_profiles.py
```

## CI runner selection

Every workflow run is evidence and must finish. Use a concurrency group unique
to `github.run_id` and `cancel-in-progress: false`; never discard a queued or
running check as superseded.

This repository is public, so `pull_request` executes untrusted fork code.
Every caller of a `NDDev-OpenNetwork/ci-workflows` reusable that exposes a `runner`
input passes `runner: ubuntu-latest` explicitly, and must keep it. Several of
those reusables default `runner` to the estate's self-hosted `amsterdam`
label, and a default is a property of the **pinned commit**, not of this
repository — so dropping the explicit value would let a routine pin bump route
fork PRs onto trusted private infrastructure with no diff here to review. On
any ci-workflows pin bump, diff `inputs.runner.default` between the old and
new commit before merging.
