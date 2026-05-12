# Reviewer Protocol

Reviewer tracks are designed to run as parallel subagents when `ry-start` or `ry-review` explicitly invokes the review phase. They live as `.opencode/agents/flow-*-review.md` with `mode: subagent` and `hidden: true`.

## Subagent Permission

The user explicitly approved subagent usage when invoking `/ry-start` or `/ry-review`. Each spawned subagent must receive a self-contained prompt with task, scope, diff, constraints, expected output, and read-only status.

## Tracks

| Track | Agent | Focus |
| --- | --- | --- |
| Architecture | `flow-architecture-review` | boundaries, dependencies, module shape, data flow |
| Quality | `flow-quality-review` | correctness, hacks, tech debt, edge cases, error handling |
| Consistency | `flow-consistency-review` | conventions, naming, style, file placement, public API shape |
| Integration | `flow-integration-review` | cross-module synchronization, contracts, migrations, configs |
| Verification | `flow-verification-review` | tests, manual checks, browser/server evidence, quality gates |
| Security | `flow-security-review` | security-sensitive paths, OWASP, secrets, auth/authz, unsafe flows |

## Finding Format

Each finding must include:

- Severity: `critical`, `high`, `medium`, `low`.
- Confidence: `0-100`.
- Location: file and line when possible.
- Evidence: concrete code or behavior.
- Impact: what fails or becomes harder.
- Fix: actionable correction.
- Disposition: `must-fix`, `should-fix`, `defer`, or `false-positive`.

Do not report confidence below 30. Validate confidence 30-49 in the parent workflow before acting.

## Parent Integration

The parent workflow (`ry-start` or `ry-review`) consolidates all findings, resolves contradictions with code evidence, fixes accepted findings, then reruns only the reviewer tracks that found problems.

## Agent Configuration

Reviewer agents are configured in `opencode.json` under `agent.<name>`:

- `mode: "subagent"` and `hidden: true` to prevent implicit invocation.
- `permission: { edit: "deny" }` to enforce read-only review.
- `steps: 36` for all tracks; `42` for `flow-security-review` (extra steps for variant-hunt sweep).
- `temperature: 0.1` for deterministic analysis.
- Distinct `color` per track for visual differentiation.
- Short orchestration-focused descriptions to discourage implicit invocation.

Orchestrators (`ry-start`, `ry-review`) invoke them via `@agent_name` in their workflow steps.
