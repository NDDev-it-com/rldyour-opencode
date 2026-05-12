---
name: ry-review
description: "Глубокое ревью: diff, PR, scope с research и reviewer tracks. Report-only по умолчанию. Use for ry-review, review, audit diff, проверь реализацию, сделай ревью, найди проблемы."
---

# ry-review

## Purpose

Find real issues before merge or deploy. Default mode is report-only: do not edit files unless the user explicitly asks after seeing findings.

## Workflow

1. Determine review target: current diff, branch vs main, PR, file scope, or prompt scope.
2. Initialize missing context with `ry-init` if needed.
3. Use Serena to map changed symbols and affected integration graph. Prefer `mcp__serena__find_symbol`, `mcp__serena__get_symbols_overview`, and `mcp__serena__find_referencing_symbols` before raw file reads.
4. Use `ry-explore` for current implementation best practices when the review depends on external technology behavior. Prefer Context7 MCP for official versioned docs, DeepWiki MCP for public repo architecture, and Grep MCP for real production usage patterns.
5. Run reviewer tracks. Use subagents when the review request or `ry-start` review phase calls for parallel review. Reviewer subagents are defined in `.opencode/agents/` with `mode: subagent`, `hidden: true`, `permission: { edit: "deny" }`.
6. Consolidate findings by severity and confidence. Validate uncertain findings with code evidence.
7. Output Russian report with exact paths, impact, suggested fixes, and whether each finding is must-fix.

## Reviewer Tracks

Read `references/reviewer-protocol.md`. These tracks are orchestrated by `ry-review` or `ry-start`; they are not broad implicit-entry skills.

- Architecture review: module boundaries, layer violations, coupling, abstraction quality.
- Quality review: code smells, duplication, dead code, error handling, naming, readability.
- Consistency review: pattern alignment, naming conventions, import structure, style uniformity.
- Integration review: API contracts, data flow, cross-module interactions, breaking changes.
- Verification review: test coverage, edge cases, regression risk, observable behavior.
- Security review (`flow-security-review`): when scope is sensitive or explicitly requested.

Each track produces findings with:
- **Path**: exact file and line reference.
- **Severity**: must-fix / should-fix / nit / observation.
- **Confidence**: high / medium / low — low-confidence findings must include the evidence gap.
- **Description**: what is wrong and why it matters.
- **Suggested fix**: concrete remediation or next step.

## Output

Report in Russian:

- Review target and scope.
- Summary by severity (must-fix / should-fix / nit / observation).
- Per-finding detail with path, impact, confidence, and suggested fix.
- Overall assessment and recommendation (merge / merge with fixes / block).
- Uncertain findings with evidence gaps clearly marked.
