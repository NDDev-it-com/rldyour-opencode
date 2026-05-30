---
description: "Проектирование нового проекта: скептические вопросы → research → архитектура docs → optional scaffold. Plan a new project with skeptical questions and research."
agent: build
---

Plan a new project before or alongside initial scaffold:

1. Ask skeptical questions in Russian about requirements, constraints, scale, timeline, and user expectations. Challenge assumptions. Offer 2-3 concrete options when scope is ambiguous.
2. Research best technologies and patterns with @ry-explore: official docs (Context7), repo architecture (DeepWiki), production patterns (Grep), web validation for gaps.
3. Use Sequential Thinking MCP for architecture and technology decisions (minimum 3 thoughts per decision).
4. Write project design documents in .serena/newproj/<project>/:
   - 01_HLO.md — high-level overview
   - 02_REQUIREMENTS.md — functional and non-functional requirements
   - 03_ARCHITECTURE.md — architecture decision and boundaries
   - 04_ADRS.md — architecture decision records (MADR 4.0.0)
   - 05_TECH_STACK.md — technology choices with justification
   - 06_API.md — API contracts
   - 07_DATA.md — data model and storage
   - 08_INFRA.md — infrastructure and deployment
   - 09_SECURITY.md — security considerations
   - 10_TESTING.md — testing strategy
   - 11_PROJECT_STRUCTURE.md — directory and module layout
   - 12_CONVENTIONS.md — coding conventions
   - 13_DELIVERY_PLAN.md — delivery milestones
5. Scaffold policy: documents first. Minimal scaffold is allowed only after the user approves it and only when it activates a useful Serena project structure without creating junk.
6. Do not create code without explicit approval.

Reply in Russian unless the owner explicitly requests another language.

Reference: references/flow-lifecycle.md
