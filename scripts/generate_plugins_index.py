#!/usr/bin/env python3
"""Generate `.opencode/plugins/index.json` — a machine-readable map of every
plugin TypeScript source + hooks it subscribes to + curated metadata.

Companion to `scripts/generate_skills_index.py` and
`scripts/generate_commands_index.py`. Same pattern, same `--check` contract.

The index lets external audits and sister marketplaces consume the
plugin-to-hook-to-MCP routing contract without parsing 10 TypeScript
files. CI verifies that the committed index matches the generator output,
so a removed hook subscription or a new plugin without metadata surfaces
as a test failure rather than silent drift.

Source of truth: the plugin source files (the hook keys returned in the
`Hooks` object) are authoritative for `hooks`. Curated fields
(`description`, `category`, adapter metadata, etc.) live in this
script and must be updated when new plugins are added.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR = REPO_ROOT / ".opencode" / "plugins"
INDEX_PATH = PLUGINS_DIR / "index.json"

# Every plugin in the marketplace. Order is alphabetical for index
# determinism. Update this dict when adding a plugin; the generator will
# emit a structural error if a plugin file on disk has no metadata entry.
PLUGIN_METADATA: dict[str, dict[str, Any]] = {
    "ry-bootstrap": {
        "description": (
            "Быстрый старт с контекстом сессии и безопасной обработкой "
            "compaction. EN: session bootstrap logs session.created, pushes "
            "MCP/workflow context, and disables synthetic autocontinue on overflow."
        ),
        "category": "lifecycle",
        "writes_files": False,
        "network": False,
    },
    "ry-command-audit": {
        "description": (
            "Аудит slash-команд без секретов и с ограниченным размером журнала. "
            "EN: appends one credential-sanitized command.execute.before line "
            "to .serena/.command_audit.log with a 256 KiB rolling cap."
        ),
        "category": "observability",
        "writes_files": True,
        "network": False,
    },
    "ry-env-protection": {
        "description": (
            "Защита чувствительных путей и data-movement команд, не DLP. "
            "EN: best-effort guardrail blocks read/bash on .env*, .pem, .key, "
            ".ssh/, .gnupg/, .aws/ and cp/mv/tar/zip/base64/dd/socat patterns."
        ),
        "category": "guardrail",
        "writes_files": False,
        "network": False,
    },
    "ry-flow-hooks": {
        "description": (
            "Подсказки после git-мутаций и напоминание о /ry-sync. EN: "
            "post-bash advice checks Conventional Commits output and nudges "
            "after commit/merge/cherry-pick/rebase changes."
        ),
        "category": "advisory",
        "writes_files": False,
        "network": False,
    },
    "ry-permission-events": {
        "description": (
            "Наблюдение permission events без enforcement. EN: logs "
            "permission.asked and permission.replied bus events through the "
            "generic event hook; enforcement stays in ry-shell-strategy."
        ),
        "category": "observability",
        "writes_files": False,
        "network": False,
    },
    "ry-shell-strategy": {
        "description": (
            "Гардрейл Shell/Git и non-interactive env hardening. EN: "
            "tool.execute.before blocks force-push without lease, catastrophic "
            "rm -rf, --no-verify pushes, and sets safe shell.env defaults."
        ),
        "category": "guardrail",
        "writes_files": False,
        "network": False,
    },
    "ry-sync-reminder": {
        "description": (
            "Ненавязчивое напоминание о финальной синхронизации. EN: "
            "session-idle toast-only nudge to run /ry-sync before ending the "
            "session, without log spam between events."
        ),
        "category": "advisory",
        "writes_files": False,
        "network": False,
    },
    "ry-system-context": {
        "description": (
            "Контекст runtime в system prompt с sanitization ветки/HEAD. EN: "
            "injects date/branch/head/worktree-dirty stamp through "
            "experimental.chat.system.transform with TTL cache, timeout, and "
            "branch/HEAD sanitization against indirect prompt injection."
        ),
        "category": "context-injection",
        "writes_files": False,
        "network": False,
    },
    "ry-tool-hints": {
        "description": (
            "Подсказки маршрутизации прямо в описаниях MCP tools. EN: appends "
            "tool.definition hints for known MCP tools so the LLM sees the "
            "AGENTS.md Tool Priority matrix inline."
        ),
        "category": "routing",
        "writes_files": False,
        "network": False,
        "requires_mcp": [
            "serena",
            "context7",
            "deepwiki",
            "grep",
            "chrome-devtools",
            "sequential-thinking",
        ],
    },
    "ry-tools": {
        "description": (
            "Диагностические custom tools с timeout и output budget. EN: "
            "registers rldyour_validate_config, _check_deps, _lsp_health, "
            "_git_audit, and _context_status wrappers around diagnostic scripts."
        ),
        "category": "tool-registration",
        "writes_files": False,
        "network": False,
        "registers_tools": [
            "rldyour_validate_config",
            "rldyour_check_deps",
            "rldyour_lsp_health",
            "rldyour_git_audit",
            "rldyour_context_status",
        ],
    },
}

# Patterns used to extract the hook subscription set from a plugin source.
# The plugin SDK returns a Hooks object where keys are hook names. We match
# both string-key form (`"tool.execute.before": ...`) and bare-identifier
# form (`event: ...`). Recognised hook names are listed in the
# @opencode-ai/plugin@1.17.12 SDK; unknown keys are surfaced as warnings.
RECOGNISED_HOOKS = {
    "event",
    "config",
    "tool",
    "tool.definition",
    "tool.execute.before",
    "tool.execute.after",
    "shell.env",
    "chat.message",
    "chat.params",
    "chat.headers",
    "command.execute.before",
    "auth",
    "provider",
    "experimental.chat.messages.transform",
    "experimental.chat.system.transform",
    "experimental.session.compacting",
    "experimental.compaction.autocontinue",
    "experimental.text.complete",
}

# Match `"hook.name":` and `bareIdent:` at indentation 2-6 inside a
# returned `Hooks` object. Conservative — does not try to parse arbitrary
# TS; the plugins all follow the same `return { ... }` shape. The value
# side can be `async (...)`, a function call (`tool: buildTools(getCwd)`),
# or any other expression — we accept all of them but immediately filter
# the captured key against RECOGNISED_HOOKS so non-hook properties drop.
HOOK_KEY_RE = re.compile(
    r'^\s{2,6}"([a-z][a-z0-9_.]*)"\s*:|^\s{2,6}([a-z][a-zA-Z0-9_]*)\s*:',
    re.MULTILINE,
)


def extract_hooks(plugin_path: Path) -> list[str]:
    src = plugin_path.read_text(encoding="utf-8")
    hooks: set[str] = set()
    for match in HOOK_KEY_RE.finditer(src):
        candidate = match.group(1) or match.group(2)
        if candidate in RECOGNISED_HOOKS:
            hooks.add(candidate)
    return sorted(hooks)


def build_index() -> dict[str, Any]:
    plugins: list[dict[str, Any]] = []
    for plugin_path in sorted(PLUGINS_DIR.glob("*.ts")):
        slug = plugin_path.stem
        metadata = dict(PLUGIN_METADATA.get(slug, {}))
        relative_path = plugin_path.relative_to(REPO_ROOT).as_posix()
        hooks = extract_hooks(plugin_path)
        plugins.append(
            {
                "name": slug,
                "path": relative_path,
                "category": metadata.pop("category", "unknown"),
                "description": metadata.pop("description", ""),
                "hooks": hooks,
                "writes_files": metadata.pop("writes_files", False),
                "network": metadata.pop("network", False),
                **metadata,
            },
        )
    return {
        "version": (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "generated_by": "scripts/generate_plugins_index.py",
        "count": len(plugins),
        "plugins": plugins,
    }


def _verify(index: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    on_disk = {p.stem for p in PLUGINS_DIR.glob("*.ts")}
    missing_metadata = on_disk - set(PLUGIN_METADATA.keys())
    for slug in sorted(missing_metadata):
        problems.append(f"plugin {slug!r} on disk but missing PLUGIN_METADATA entry")
    orphan = set(PLUGIN_METADATA.keys()) - on_disk
    for slug in sorted(orphan):
        problems.append(f"plugin {slug!r} has metadata but no .ts file on disk")
    for plugin in index["plugins"]:
        if plugin["category"] == "unknown":
            problems.append(f"plugin {plugin['name']!r} has no category in PLUGIN_METADATA")
        if not plugin["hooks"]:
            problems.append(f"plugin {plugin['name']!r} extracts to zero hooks — generator may be stale")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify .opencode/plugins/index.json")
    parser.add_argument("--check", action="store_true", help="Verify committed index matches generator output")
    parser.add_argument("--strict", action="store_true", help="Treat structural problems as fatal")
    args = parser.parse_args(argv)

    index = build_index()
    rendered = json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    structural = _verify(index)

    if args.check:
        committed = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""
        if committed != rendered:
            print(
                "[FAIL] .opencode/plugins/index.json is out of sync with the .ts files.\n"
                "Regenerate via: python3 scripts/generate_plugins_index.py",
                file=sys.stderr,
            )
            return 1
        if structural and args.strict:
            for problem in structural:
                print(f"[FAIL] {problem}", file=sys.stderr)
            return 1
        for problem in structural:
            print(f"[WARN] {problem}", file=sys.stderr)
        print(f"[OK] {INDEX_PATH.name}: {index['count']} plugins, in sync")
        return 0

    INDEX_PATH.write_text(rendered, encoding="utf-8")
    print(f"[OK] wrote {INDEX_PATH.relative_to(REPO_ROOT)} ({index['count']} plugins)")
    for problem in structural:
        print(f"[WARN] {problem}", file=sys.stderr)
    if structural and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
