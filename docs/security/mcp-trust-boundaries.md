# MCP Trust Boundaries

This document classifies every MCP server declared in `opencode.json` by trust
class. Use it when deciding which MCP to call from a skill, which to enable in
CI, and which to gate behind explicit user authorization. It complements
`docs/observability.md` (triage) and `.opencode/plugins/ry-env-protection.ts`
(read-side guardrail — best-effort, not DLP).

## Trust classes

- **trusted-official**: First-party MCP from the upstream project, signed
  releases, used as canonical documentation source. Safe in CI smoke and live
  modes.
- **trusted-public**: Third-party but widely used, open source, no secrets
  required. Safe in CI smoke modes. Live modes acceptable.
- **local-only**: Spawned on-host via `bunx` / `uvx` / system binary. No
  network beyond the spawn; reads project files. Safe in CI when the launcher
  is on PATH.
- **secrets-required**: Remote endpoint that needs an env var token. Skipped
  in CI smoke when the secret is absent.
- **network-optional**: Remote endpoint that works without auth but with
  reduced rate limits if the API key is missing.

## 11 servers (opencode.json @ HEAD)

| Server | Type | Trust class | Secrets | Network | Repo read | Repo write | CI mode |
|---|---|---|---|---|---|---|---|
| `serena` | local (uvx) | local-only | none | none | yes | no | local-launch |
| `sequential-thinking` | local (bunx) | local-only | none | none | no | no | local-launch |
| `chrome-devtools` | local (bunx) | local-only | none | yes (target site) | no | no | local-launch |
| `shadcn` | local (bunx) | local-only | none | yes (registry) | no | yes (component scaffold) | local-launch |
| `dart-flutter` | local (dart) | local-only | none | none | yes | yes | local-launch |
| `context7` | remote | trusted-public | optional `CONTEXT7_API_KEY` (rate limit) | yes | no | no | remote-head |
| `deepwiki` | remote | trusted-public | none | yes | no | no | remote-head |
| `grep` | remote | trusted-public | none | yes | no | no | remote-head |
| `figma` | remote | trusted-official | optional Figma OAuth token | yes | no | no | remote-head, secrets-required for live |
| `github` | remote | trusted-official | required `GITHUB_PERSONAL_ACCESS_TOKEN` (fine-grained PAT, minimal scopes) | yes | yes (via PAT) | yes (via PAT) | secrets-required |
| `openai-docs` | remote | trusted-official | none | yes | no | no | remote-head |

## CI mode reference

- **static**: parses `opencode.json`, no spawn, no network. Always safe.
- **local-launch**: spawns the local launcher with a short window. Requires
  the launcher (bunx/uvx/dart) on PATH; skipped otherwise.
- **remote-head**: HEAD/GET probe against the URL. Any HTTP status counts as
  reachable, including 401/403 (proves the endpoint answered).
- **secrets-required**: same as remote-head but only fires when the relevant
  secret is present in the environment.
- **live**: real tool call against a real server. Manual / nightly only;
  never on every push.

## Operator guidance

- Tokens for `github` and `figma` should be **fine-grained, scoped to the
  minimum repositories/teams required**, and rotated quarterly. Do not use
  classic GitHub PATs except for explicit short-term troubleshooting.
- `context7` is the only remote MCP whose API key is **optional** — the
  endpoint works without authentication at a lower rate limit. Add the env
  var only when you hit a documented rate limit.
- Do not commit `.env*` files. The `ry-env-protection` plugin guards against
  obvious LLM-driven exfiltration mistakes but cannot defeat targeted
  exfiltration; rely on `gitleaks` (`secret-scan.yml`) and GitHub secret
  scanning as the durable boundary.
- When a remote MCP is unreachable in CI, prefer reporting `unreachable` and
  continuing the workflow over hard-failing — the dependency-check workflow
  publishes the smoke envelope as `GITHUB_STEP_SUMMARY` so owners can see
  the state without breaking PR merges.

## When to update this document

- A new MCP server is added to `opencode.json`. Add a row.
- A server changes provider (`uvx` → `bunx`, remote endpoint changes URL).
- A server gains or loses required-secret status.
- The smoke probe modes in `scripts/smoke_mcp_capabilities.py` change.

The CI gate `dependency-check.yml` does not parse this document directly,
but reviewers should expect it to stay in sync with the MCP list.
