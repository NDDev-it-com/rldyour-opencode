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
(`description`, `category`, `defense_in_depth_pair`, etc.) live in this
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
            "Session bootstrap. Logs a banner on session.created, pushes "
            "MCP/workflow context on experimental.session.compacting, and "
            "disables the synthetic autocontinue turn on overflow."
        ),
        "category": "lifecycle",
        "writes_files": False,
        "network": False,
    },
    "ry-command-audit": {
        "description": (
            "Slash-command audit log. Appends one credential-sanitized line "
            "per command.execute.before to .serena/.command_audit.log "
            "(256 KiB rolling cap)."
        ),
        "category": "observability",
        "writes_files": True,
        "network": False,
    },
    "ry-env-protection": {
        "description": (
            "Best-effort sensitive-path guardrail. Blocks read/bash on .env*, "
            ".pem, .key, .ssh/, .gnupg/, .aws/ paths plus data-movement "
            "utilities (cp/mv/tar/zip/base64/dd/socat/...). NOT a DLP boundary."
        ),
        "category": "guardrail",
        "writes_files": False,
        "network": False,
    },
    "ry-flow-hooks": {
        "description": (
            "Post-bash advice. Conventional Commits regex check on git commit "
            "output + /ry-sync nudge after every commit/merge/cherry-pick/"
            "rebase that changes the repo."
        ),
        "category": "advisory",
        "writes_files": False,
        "network": False,
    },
    "ry-permission-policy": {
        "description": (
            "Dynamic deny-only policy on permission.ask. Blocks force-push "
            "without lease, catastrophic rm -rf, and --no-verify pushes. "
            "Honours RY_ALLOW_NO_VERIFY=1 opt-out for symmetric coverage."
        ),
        "category": "guardrail",
        "writes_files": False,
        "network": False,
        "defense_in_depth_pair": "ry-shell-strategy",
    },
    "ry-shell-strategy": {
        "description": (
            "Unconditional shell guardrail on tool.execute.before. Same three "
            "patterns as ry-permission-policy plus shell.env hardening "
            "(GIT_TERMINAL_PROMPT=0, NO_UPDATE_NOTIFIER=1, conditional CI=1)."
        ),
        "category": "guardrail",
        "writes_files": False,
        "network": False,
        "defense_in_depth_pair": "ry-permission-policy",
    },
    "ry-sync-reminder": {
        "description": (
            "Session-idle reminder. Toast-only nudge to run /ry-sync before "
            "ending the session; no log spam between events."
        ),
        "category": "advisory",
        "writes_files": False,
        "network": False,
    },
    "ry-system-context": {
        "description": (
            "Injects [rldyour runtime] date/branch/head/worktree-dirty stamp "
            "into every system prompt via experimental.chat.system.transform. "
            "Branch and HEAD cached at factory init; status spawn has 800ms timeout."
        ),
        "category": "context-injection",
        "writes_files": False,
        "network": False,
    },
    "ry-tool-hints": {
        "description": (
            "Appends routing hints to known MCP tool descriptions via "
            "tool.definition. Encodes AGENTS.md § Tool Priority matrix in the "
            "tool itself so the LLM sees the hint inline."
        ),
        "category": "routing",
        "writes_files": False,
        "network": False,
        "requires_mcp": [
            "serena",
            "context7",
            "deepwiki",
            "grep",
            "playwright",
            "chrome-devtools",
            "semgrep",
            "sequential-thinking",
        ],
    },
    "ry-tools": {
        "description": (
            "Registers five LLM-callable custom tools (rldyour_validate_config, "
            "_check_deps, _lsp_health, _git_audit, _fullrepo_status) wrapping "
            "diagnostic scripts. Each tool has timeout + maxOutputBytes budget."
        ),
        "category": "tool-registration",
        "writes_files": False,
        "network": False,
        "registers_tools": [
            "rldyour_validate_config",
            "rldyour_check_deps",
            "rldyour_lsp_health",
            "rldyour_git_audit",
            "rldyour_fullrepo_status",
        ],
    },
}

# Patterns used to extract the hook subscription set from a plugin source.
# The plugin SDK returns a Hooks object where keys are hook names. We match
# both string-key form (`"tool.execute.before": ...`) and bare-identifier
# form (`event: ...`). Recognised hook names are listed in the
# @opencode-ai/plugin@1.15.4 SDK; unknown keys are surfaced as warnings.
RECOGNISED_HOOKS = {
    "event",
    "config",
    "tool",
    "tool.definition",
    "tool.execute.before",
    "tool.execute.after",
    "shell.env",
    "permission.ask",
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
        "version": 1,
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
