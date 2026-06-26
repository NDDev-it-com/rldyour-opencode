# Security Policy

## Supported Versions

Only the current exact numeric product release tag receives security fixes.
The `1.7.x` line label tracks only the latest released patch, not every
historical patch in the line.

| Version | Supported |
|---|---|
| Current exact tag `1.7.6` | yes |
| Older `1.1.*` tags | no; upgrade to current exact tag |
| Older minor / major lines | no |

When a security issue is reported against an unsupported version, the project will upgrade the report to the current branch instead of patching old releases.

## Reporting a Vulnerability

**Do not file public issues for security vulnerabilities.** Public disclosure before a patch is shipped puts every OpenCode marketplace operator at risk.

### Private disclosure channels

1. **GitHub Security Advisories (preferred)**: Open a private advisory at https://github.com/NDDev-it-com/rldyour-opencode/security/advisories/new. This automatically grants the maintainer access without exposing the report publicly.
2. **Email**: Send a PGP-encrypted message to the email address listed in the repository owner's GitHub profile. If PGP is not practical, plain email is acceptable for low-severity reports.

### What to include

- A clear description of the vulnerability and the threat model it breaks.
- Reproduction steps (minimal, deterministic).
- Affected component(s): plugin file, script, config key, MCP server interaction, etc.
- Potential impact (confidentiality / integrity / availability / scope).
- Suggested fix or mitigation, if you have one.
- Whether you would like public credit in the resulting advisory.

### What to expect from us

- **Acknowledgement** within 72 hours of receipt.
- **Initial assessment** within 7 days, including a severity rating against OWASP Top 10 2025 and a target patch window.
- **Coordinated disclosure**: once a fix is ready, we publish a GitHub Security Advisory with a CVE (when applicable), credit the reporter (unless they prefer anonymity), and ship the fix on `main`.
- **No legal action** against good-faith research that follows this policy.

## Scope

In scope:

- The runtime configuration in `opencode.json` and `.opencode/`.
- All plugin code in `.opencode/plugins/*.ts`.
- All scripts in `scripts/` and `scripts/tests/`.
- Documentation that affects runtime behaviour (`AGENTS.md`, ADRs, references).
- CI workflows in `.github/workflows/`.
- Dependency pin set in `.opencode/package.json` and `scripts/_extract_pins.py`.

Out of scope:

- Upstream OpenCode itself. Report those to https://github.com/anomalyco/opencode/security.
- Third-party MCP servers. Report those to their upstream project.
- Provider model behaviour (Anthropic, OpenAI, etc.) - those are vendor-side.
- Operational security of operator-managed forks unless the vulnerability is reproducible against the upstream marketplace state.

## Hardening already in place

The marketplace ships several defense-in-depth controls that vulnerability reports should be aware of:

- **`.opencode/plugins/ry-shell-strategy.ts`** unconditionally blocks `git push --force` without lease, catastrophic `rm -rf` targets (root / `$HOME` / `~` / cwd / parent dir), and `git push --no-verify` unless `RY_ALLOW_NO_VERIFY=1` is explicitly set. Dynamic enforcement uses `tool.execute.before`; `permission.ask` is forbidden as a security boundary by `scripts/check_plugin_hooks.py`.
- **`.opencode/plugins/ry-env-protection.ts`** blocks reading sensitive paths (`.env`, `.pem`, `.key`, `.p12`, `.pfx`, `.ssh/`, `.gnupg/`, `.aws/credentials`, generic `secret` / `private_key` / `service_account`) through `read` and an extended set of bash dumping / scripting / redirect patterns. `.env.example`, `.env.template`, `.env.sample` remain allowlisted.
- **`.opencode/plugins/ry-command-audit.ts`** + **`scripts/_sanitize_diag.py`** redact credential-shaped substrings (Context7 / OpenAI / Anthropic / GitHub PATs / GitLab PATs / AWS / Slack / JWT / PEM) before any text is persisted to local logs or diagnostic bundles.
- **`scripts/_validate_helpers.py`** rejects unknown permission keys against the v1.15.x canonical set; project-side defense against upstream issue `sst/opencode#15507`.
- **CI hardens** all workflows with SHA-pinned actions, least-privilege `permissions:` blocks, concurrency cancel-in-progress groups, per-job timeouts, CodeQL code-scanning upload on the public repo, and a gitleaks + dependency-review trio.

If you find a way around any of these, the report is in-scope and high priority.
