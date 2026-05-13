---
description: "Деплой с sync/checks/логами/fix-forward/финализацией. Deploy with local↔GitHub↔server sync, log verification, fix-forward, and docs/git finalization."
agent: build
---

Deploy with local/GitHub/server sync, log checks, health verification, and memory/docs/git finalization:

1. Read deploy contract from AGENTS.md, .opencode/ instruction docs, or .serena/deploy/*.md in that priority. If no contract exists, ask the user before proceeding.
2. Verify local branch, PR, quality gates, Serena memories, docs, and GitHub sync.
3. Inspect server baseline: git status, current SHA, logs before restart, disk space, process manager.
4. Pull or sync code to server.
5. Run migrations only after readiness checks and backup/rollback contract verification.
6. Restart/build services.
7. Verify logs, health, tests, and business-critical flows.
8. If deployment fails, perform RCA through logs, code, and internet research, then fix-forward. Ask the user with options for risky operations.
9. DB rollback only when an explicit rollback contract and backup/restore point are verified.
10. Finish with /ry-sync to finalize memories, docs, and git state.

Reference: references/deploy-contract.md, references/flow-lifecycle.md, references/post-task-sync.md
