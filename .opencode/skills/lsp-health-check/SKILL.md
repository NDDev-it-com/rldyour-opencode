---
name: lsp-health-check
description: "Проверка LSP и Serena prerequisites для Python/Rust/Dart/Flutter/TS/JS/Go/C++/Qt/YAML/Docker/HTML/CSS/Shell. Используй для: проверь LSP, проверь язык-серверы, диагностики LSP, доступны ли LSP в проекте. EN triggers: check LSP, language server health, LSP diagnostics, verify LSP setup, are LSP installed, LSP project prerequisites, LSP doctor."
---

# LSP Health Check

## Purpose

Verify that language servers and project prerequisites are available before relying on diagnostics, semantic navigation, or Serena symbol tools.

## Workflow

1. Check OpenCode LSP configuration: verify `opencode.json` has `"lsp": true` or appropriate per-server configuration for the project languages.
2. Detect project languages from manifests, build files, lockfiles, and source files.
3. Verify that relevant LSP servers auto-start for detected file extensions.
4. Report missing language support separately from project prerequisite warnings.
5. For C, C++, and Qt C++, treat missing `compile_commands.json` as a serious warning because diagnostics may be wrong.
6. For TypeScript and JavaScript, verify `tsconfig.json` or `jsconfig.json`.
7. For Python, verify `pyproject.toml`, `pyrightconfig.json`, or virtual environment expectations.
8. For Dart and Flutter, verify `pubspec.yaml`, `analysis_options.yaml`, and dependency resolution.
9. Do not start raw `stdio` LSP sessions as a test - they hang waiting for a real LSP client.

## Default LSP Availability

OpenCode has 30+ built-in LSP servers that auto-start when file extensions are detected. These include:

- Pyright (Python), typescript-language-server (TS/JS), rust-analyzer (Rust), dart analysis server (Dart/Flutter), gopls (Go), clangd (C/C++), and many more.

If `"lsp": true` is set in `opencode.json`, these auto-start. If specific configuration is needed, use the `lsp` object in `opencode.json` for per-server overrides.

## Output

In Russian, summarize:

- Available and missing LSP support.
- Project prerequisite warnings.
- What must be installed or configured next.
- Whether Serena semantic work is safe for the detected languages.
- OpenCode LSP configuration status.

## Anti-patterns

- Running `pyright-langserver --stdio` without an LSP client (hangs).
- Ignoring project prerequisite warnings (`compile_commands.json` for C/C++ is critical).
- Claiming "LSPs work" without verification through OpenCode configuration or `command -v`.
- Reinstalling already working executables only for package manager standardization.