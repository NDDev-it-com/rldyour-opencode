---
description: "Глубокое исследование через ry-explore (Opus, max effort). Run deep multi-source research."
agent: ry-explore
subtask: true
---

Глубокое исследование темы / Deep research topic: **$ARGUMENTS**

Run the full ry-explore workflow:

1. **MCP-first phase** — Context7 (`mcp__context7__resolve-library-id` → `mcp__context7__get-library-docs`) → DeepWiki (`mcp__deepwiki__*`) → Grep (`mcp__grep__*`). Pull authoritative quotes, file paths, version numbers, section anchors.
2. **Web validation phase** — only if MCP gaps remain (current events, recent releases ≤6 months, security advisories, vendor announcements).
3. **Cross-validation** — verify any critical or contested claim against ≥2 independent sources; surface contradictions explicitly, do not pick silently.
4. **Synthesis** — produce a structured report with **Finding / Confidence / Details** sections per finding, plus a "Sources consulted" section at the end.

Every claim carries a confidence label (Confirmed / Strongly supported / Inferred) and an explicit source citation.

If `$ARGUMENTS` is in Russian — reply in Russian. Otherwise reply in English. Source citations stay in their original language.