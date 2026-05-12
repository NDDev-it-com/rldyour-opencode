---
name: lsp-setup
description: "Установка/обновление LSP-серверов через brew + toolchain (rustup, dart, npm). Только по явному запросу. Используй для: установи LSP, обнови лсп, поставь язык-серверы, почини language server. EN triggers: install LSP, install language server, update LSP, fix LSP, brew LSP, set up language server, bootstrap LSPs."
---

# LSP Setup

## Purpose

Install or update LSP dependencies only after an explicit user request. Keep setup deterministic, brew-first, and safe for long-lived `stdio` language server use.

## Rules

- Prefer Homebrew for missing system tools.
- Use `rustup component add rust-src rust-analyzer` when `rustup` is installed.
- For npm-only LSPs (typescript-language-server, yaml-language-server, bash-language-server) install globally: `npm install -g <package>`. Or use existing project-local install when one exists.
- Do not reinstall already working non-brew commands just to standardize ownership.
- Do not put machine-local executable paths into committed project files.
- Do not auto-edit `.serena/project.yml`; propose or apply changes only on explicit setup request.
- After setup, run `lsp-health-check` and report exact remaining gaps.

OpenCode has 30+ built-in LSP servers that auto-start when `"lsp": true` is set in `opencode.json`. For custom LSP configuration, use the `lsp` object in `opencode.json` for per-server overrides.

## Install Profile Reference

Read `references/install-profiles.md` before changing install commands or adding new LSPs.

## Anti-patterns

- Installing LSPs silently without explicit user request.
- `bunx package --stdio` / `uvx package --stdio` as long-lived runtime.
- Reinstalling working executables just to change package manager.
- Auto-editing `.serena/project.yml` without explicit setup request.
- Hardcoding user-local paths (`/opt/homebrew/...`, `/home/user/...`) in committed plugin files.