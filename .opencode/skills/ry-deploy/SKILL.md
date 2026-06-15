---
name: ry-deploy
description: "Полный цикл деплоя: sync, checks, logs, фикс, финализация. Используй для: задеплой, деплой на сервер, прод, выкати в продакшен. EN triggers: ry-deploy, deploy server, production deploy, ship to prod, rollout, deploy lifecycle, deploy verification, fix-forward."
---

# ry-deploy

## Purpose

Synchronize local repository, GitHub, and server, then deploy safely with evidence. Automation is expected, but risky operations require code/log evidence and user questions with options.

## Workflow

1. Read deploy contract from `AGENTS.md`, then `.serena/deploy/*.md` if present. The deploy contract defines server addresses, sync methods, migration commands, health checks, and rollback procedures.
2. Run readiness checks before any push:
   - `bash scripts/deploy_readiness.sh <target>` - single-shot deploy preflight composite (working tree clean of real changes, on `main`, in sync with upstream, Serena memories present, project-native test/lint commands detected).
   - `bash scripts/git_sync_audit.sh` - exact dirty file list (whitelist-aware), worktree count, merged-branch cleanup candidates.
   - `bash scripts/validate_config.sh` + `python3 -m pytest scripts/tests/` - same gates CI runs.
   Stop on any FAIL and surface the exact blocker before continuing.
3. Inspect server baseline: git status, current commit, disk, logs before restart, process manager.
4. Sync code to server.
5. Run migrations only when readiness is clear and the deploy contract defines a migration command.
6. Restart/build services.
7. Run postflight verification: logs, tests, health checks, and critical behavior.
8. If anything fails, perform root cause analysis using server logs, code, and internet research. Fix-forward and redeploy. Ask the user with options for risky or ambiguous decisions.
9. DB rollback only when explicit rollback command and backup/restore point are verified.
10. Finish with `flow-post-task-sync`.

## Deploy Contract Reference

The deploy contract should specify:

- **Server**: hostname, SSH access, working directory.
- **Sync method**: git pull, rsync, CI/CD pipeline.
- **Build**: commands and environment.
- **Migrations**: command, when to run, rollback command.
- **Restart**: process manager (systemd, pm2, docker), restart command.
- **Health checks**: URLs, expected status, timeout.
- **Logs**: log locations, error patterns to watch.
- **Rollback**: git revert, DB restore, service restart sequence.

If the deploy contract is missing, report the gap in Russian and ask the user to define it before proceeding with the deploy.

## No Fake Success

If auth, missing credentials, server access, or unavailable health checks prevent validation, state the limitation and what evidence was still collected. Do not report success without verification.

## Output

Report in Russian:

- Deploy target and contract status.
- Pre-deploy state: local git, server baseline, readiness checks.
- Deploy steps performed with evidence.
- Post-deploy verification: logs, health checks, critical behavior.
- Issues encountered and resolution.
- Final state: commit, branch, memories, docs sync status.
