#!/usr/bin/env python3
"""Extract pinned dependency versions from opencode.json.

Walks `mcp.<name>.command` arrays and emits a JSON document listing every
detected pin (npm via bunx, Python via uvx, Dart SDK reference). Used by
`scripts/check_deps_freshness.sh` and any future freshness automation.

Output JSON envelope (stdout):

    {
        "pins": [
            {
                "kind": "npm" | "pypi" | "dart",
                "server": str,   # opencode.json mcp.<server> key
                "name": str,     # package name (or "dart-sdk" for Dart)
                "version": str   # pinned version (or "system" for Dart)
            },
            ...
        ],
        "count": int
    }

Consumers depend on this exact shape; do not rename fields without a
PATCH/MINOR bump and an entry in CHANGELOG.md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NPM_BUNX_RE = re.compile(r"^(?:@?[\w./-]+)@([0-9][\w.+\-]*)$")
UV_FROM_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([0-9][\w.+\-]*)$")


def extract_pins(cfg_path: Path) -> list[dict[str, str]]:
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    pins: list[dict[str, str]] = []
    for server_name, server in (cfg.get("mcp") or {}).items():
        if server.get("type") != "local":
            continue
        cmd = server.get("command") or []
        if not cmd:
            continue
        if cmd[0] == "bunx":
            # bunx <package>@<version> [...args]
            for token in cmd[1:]:
                if token.startswith("-"):
                    continue
                m = NPM_BUNX_RE.match(token)
                if m:
                    pkg = token.rsplit("@", 1)[0]
                    pins.append({
                        "kind": "npm",
                        "server": server_name,
                        "name": pkg,
                        "version": m.group(1),
                    })
                    break
        elif cmd[0] == "uvx":
            # uvx --from <pkg>==<ver> ... <pkg> ...
            for i, token in enumerate(cmd):
                if token == "--from" and i + 1 < len(cmd):
                    m = UV_FROM_RE.match(cmd[i + 1])
                    if m:
                        pins.append({
                            "kind": "pypi",
                            "server": server_name,
                            "name": m.group(1),
                            "version": m.group(2),
                        })
                        break
        elif cmd[0] == "dart":
            pins.append({
                "kind": "dart",
                "server": server_name,
                "name": "dart-sdk",
                "version": "system",
            })
    return pins


def main(argv: list[str]) -> int:
    """Entry point.

    Usage: _extract_pins.py <opencode.json>
    Emits JSON {"pins": [...], "count": <n>} to stdout.
    Each pin: {"kind": "npm"|"pypi"|"dart", "server", "name", "version"}.
    """
    if len(argv) < 2:
        print("usage: _extract_pins.py <opencode.json>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2
    pins = extract_pins(path)
    print(json.dumps({"pins": pins, "count": len(pins)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
