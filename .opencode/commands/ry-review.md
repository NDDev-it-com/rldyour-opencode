---
description: "Deep review with research and reviewer tracks"
agent: plan
---

Deep review of a diff, PR, branch, or scope with research and reviewer subagents. Read-only by default.

1. Identify review target: diff, branch, PR, scope, or prompt.
2. Read Serena memories and project instruction docs for context.
3. Research the affected integration graph via Serena: symbols, references, data contracts.
4. Invoke reviewer subagents in parallel:
   - @flow-architecture-review: boundaries, dependency direction, public API, data flow.
   - @flow-quality-review: correctness, completeness, edge cases, error handling.
   - @flow-consistency-review: naming, style, imports, public API shape.
   - @flow-integration-review: cross-module contracts, schemas, configs, backward compatibility.
   - @flow-verification-review: tests, quality gates, browser/server evidence.
   - @flow-security-review: only when scope is security-sensitive or explicitly requested.
5. Consolidate all findings, resolve contradictions with code evidence.
6. Produce a Russian report with exact paths, severity, confidence, evidence, impact, and fixes.

Reference: references/reviewer-protocol.md, references/flow-lifecycle.md
