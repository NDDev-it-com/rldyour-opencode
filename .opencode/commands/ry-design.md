---
description: "Сквозной дизайн-воркфлоу: Figma + tokens + FSD + shadcn/ui + browser validation. Run end-to-end design workflow."
agent: build
---

Сквозной дизайн-воркфлоу для: **$ARGUMENTS**

Use the `ry-design` skill to run the end-to-end rldyour design implementation workflow. The skill orchestrates the four specialized design skills and the browser-validation handoff.

Workflow the skill enforces:

1. **Scope** — target page/component, Figma source, required states, responsive frames, business behavior, acceptance criteria.
2. **Figma context** (if available) — `figma-to-code` extracts frames, variables, components, layout data, assets, Code Connect hints via `figma_*`.
3. **Tokens** — `design-system-implementation` centralizes color/typography/spacing/radius/shadow/motion tokens before scattering raw values; W3C DTCG / Tailwind v4 CSS-variables form preferred.
4. **Architecture** — `fsd-frontend-architecture` decides FSD layer placement (`shared`/`entities`/`features`/`widgets`/`pages`/`app`) and public API.
5. **Components** — shadcn MCP via `shadcn_*` (Browse / Search / Install) for primitives and registry blocks; ReactBits.dev only for purposeful motion or interactive effects.
6. **Implementation** — Serena-first inspection (`get_symbols_overview` → `find_symbol`), then code; never paste generated code blindly.
7. **Validation** — `design-validation` + `browser-validation` (Playwright `playwright_*` + Chrome DevTools `chrome-devtools_*`) for pixel-perfect, responsive, runtime, business-logic checks.
8. **Sync** — durable design-system facts → `serena-memory-sync` for future sessions.

Browser artifacts go under `browser/` and are not committed.

Reply in Russian when the scope is described in Russian.