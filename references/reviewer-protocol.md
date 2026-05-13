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

Reviewer agents are configured per file in `.opencode/agents/<name>.md` (single source of truth — never duplicated in `opencode.json`):

- `mode: "subagent"` and `hidden: true` to prevent implicit invocation. Hidden subagents are not in `@`-autocomplete and run only when the orchestrator explicitly invokes them via `@flow-<track>-review` or the Task tool.
- `permission: { edit: "deny" }` enforces read-only review at the runtime layer. Bash is restricted to a git-only allowlist (`git diff/log*/show*/status*`) so reviewers can read history but cannot mutate state.
- `model: anthropic/claude-sonnet-4-6` for every track. Sonnet 4.6 is the cost / latency sweet spot for diff-scale review: large enough context to ingest the changed scope plus integration neighbours, fast enough that six parallel reviewers complete within a single user wait window, and consistent enough at `temperature: 0.1` to give reproducible findings. Opus 4.7 is reserved for `@ry-explore` (multi-source research with 1M context) and is not used for reviewers — Opus latency would dominate the parallel fan-out.
- `steps: 36` for all tracks; `42` for `flow-security-review`. The extra 6 steps reserve budget for the variant-hunt sweep — once a security finding is confirmed, the reviewer searches sibling files / similar patterns for the same root cause instead of stopping at the first occurrence. Other tracks do not need this widened search because their finding shape is local to the touched diff.
- `temperature: 0.1` keeps reviewers deterministic; the same diff and prompt should produce the same finding set on repeat. Sampling at higher temperatures introduces phantom findings that the parent workflow then has to dismiss as false-positive.
- Distinct `color` (hex `^#[0-9a-fA-F]{6}$` or enum `primary|secondary|accent|success|warning|error|info`) per track for TUI visual differentiation.
- Short orchestration-focused `description` (≤200 chars) — long descriptions tempt the router to invoke reviewers implicitly outside the `ry-start`/`ry-review` orchestration window.

Orchestrators (`ry-start`, `ry-review`) invoke them via `@agent_name` in their workflow steps and pass a self-contained prompt (see `Subagent Permission` above).
