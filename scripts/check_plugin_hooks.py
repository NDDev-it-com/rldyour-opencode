#!/usr/bin/env python3
"""Validate OpenCode plugin hook usage against the pinned runtime contract.

The current OpenCode v1.17.5 baseline has three materially different hook classes:

- documented hooks/events from https://opencode.ai/docs/plugins/
- SDK/runtime hooks present in @opencode-ai/plugin and triggered by the
  v1.15.4 source tree and still allowed through the current baseline, but omitted
  from the public docs event list
- typed-but-untriggered surfaces, most notably `permission.ask`

This validator keeps the marketplace honest: security enforcement must use
static permission config plus deterministic `tool.execute.before` guards, not
a hook that exists in TypeScript types but is not called by the runtime.
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

DOCUMENTED_HOOKS = frozenset(
    {
        "event",
        "config",
        "tool",
        "tool.execute.before",
        "tool.execute.after",
        "shell.env",
        "experimental.session.compacting",
    }
)

SDK_RUNTIME_HOOKS = frozenset(
    {
        "auth",
        "provider",
        "chat.message",
        "chat.params",
        "chat.headers",
        "command.execute.before",
        "experimental.chat.messages.transform",
        "experimental.chat.system.transform",
        "experimental.compaction.autocontinue",
        "experimental.text.complete",
        "tool.definition",
    }
)

FORBIDDEN_HOOKS = {
    "permission.ask": (
        "OpenCode SDK types expose this hook, but v1.15.4 source/runtime "
        "inspection shows the permission service publishes permission.asked/"
        "permission.replied events and does not trigger plugin permission.ask; "
        "the current v1.17.5 baseline keeps it forbidden for enforcement."
    )
}

EVENT_TYPES_ONLY = frozenset(
    {
        "permission.asked",
        "permission.replied",
        "command.executed",
        "session.created",
        "session.idle",
    }
)

ALLOWED_HOOKS = DOCUMENTED_HOOKS | SDK_RUNTIME_HOOKS

HOOK_KEY_RE = re.compile(
    r'^\s{2,6}"([^"]+)"\s*:|^\s{2,6}(event|config|tool|auth|provider)\s*:',
    re.MULTILINE,
)


def _strip_comments(source: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)


def extract_hook_keys(source: str) -> set[str]:
    """Extract hook-like keys from a plugin source.

    The plugins all return a Hooks object, but some files also contain maps
    with string keys (for example MCP tool hints). To avoid false positives,
    only dotted string keys and the five bare top-level hook names are treated
    as hook candidates.
    """
    hooks: set[str] = set()
    for match in HOOK_KEY_RE.finditer(source):
        candidate = match.group(1) or match.group(2)
        if candidate in {"event", "config", "tool", "auth", "provider"} or "." in candidate:
            hooks.add(candidate)
    return hooks


def validate_plugin(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    code_only = _strip_comments(source)
    hooks = extract_hook_keys(code_only)
    problems: list[str] = []
    warnings: list[str] = []

    for hook in sorted(hooks):
        if hook in FORBIDDEN_HOOKS:
            problems.append(f"{path.name}: forbidden hook {hook!r}: {FORBIDDEN_HOOKS[hook]}")
        elif hook in EVENT_TYPES_ONLY:
            problems.append(
                f"{path.name}: {hook!r} is an event.type value, not a top-level plugin hook; "
                "handle it inside the generic `event` hook"
            )
        elif hook not in ALLOWED_HOOKS:
            warnings.append(f"{path.name}: unknown hook-like key {hook!r}; verify before relying on it")

    if path.name in {"ry-env-protection.ts", "ry-shell-strategy.ts"} and "tool.execute.before" not in hooks:
        problems.append(f"{path.name}: security guard plugins must subscribe to tool.execute.before")
    if path.name == "ry-shell-strategy.ts" and "shell.env" not in hooks:
        problems.append("ry-shell-strategy.ts: shell strategy must keep shell.env injection")

    return {
        "plugin": path.name,
        "hooks": sorted(hooks),
        "problems": problems,
        "warnings": warnings,
    }


def validate_all() -> dict[str, Any]:
    plugins = [validate_plugin(path) for path in sorted(PLUGINS_DIR.glob("*.ts"))]
    return {
        "ok": not any(p["problems"] for p in plugins),
        "plugins": plugins,
        "allowed_hooks": sorted(ALLOWED_HOOKS),
        "forbidden_hooks": sorted(FORBIDDEN_HOOKS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate OpenCode plugin hook usage.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable results.")
    args = parser.parse_args(argv)

    result = validate_all()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for plugin in result["plugins"]:
            hooks = ", ".join(plugin["hooks"]) or "(none)"
            print(f"[OK] {plugin['plugin']}: hooks={hooks}")
            for warning in plugin["warnings"]:
                print(f"[WARN] {warning}", file=sys.stderr)
            for problem in plugin["problems"]:
                print(f"[FAIL] {problem}", file=sys.stderr)
        if result["ok"]:
            print(f"[OK] plugin hook contract valid ({len(result['plugins'])} plugin files)")
        else:
            print("[FAIL] plugin hook contract has blocking problems", file=sys.stderr)

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
