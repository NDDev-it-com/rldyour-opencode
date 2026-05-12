#!/usr/bin/env python3
"""Validation helpers for rldyour-opencode.

All Python validation logic for scripts/validate_config.sh lives here.
Single-file Python module avoids zsh-heredoc escaping issues that break
inline `python3 -c` blocks under `set -euo pipefail`.

Exit code: 0 on success, 1 on any validation error. Each invocation
prints `[OK]` or `[ERR]` lines to stdout and returns non-zero on errors.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def validate_opencode_json(path: Path) -> int:
    """Validate top-level opencode.json shape."""
    errors = 0
    try:
        cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        print(f"[ERR] {path}: JSON decode error: {exc}")
        return 1

    if "model" not in cfg:
        print("[ERR] Missing required top-level key: model")
        errors += 1
    else:
        print(f"[OK] Top-level key present: model = {cfg['model']}")

    for name, agent in (cfg.get("agent") or {}).items():
        mode = agent.get("mode")
        if mode and mode not in ("primary", "subagent"):
            print(f"[ERR] Agent {name!r}: invalid mode: {mode!r}")
            errors += 1

        edit = (agent.get("permission") or {}).get("edit")
        if isinstance(edit, str) and edit not in ("allow", "ask", "deny"):
            print(f"[ERR] Agent {name!r}: invalid edit permission: {edit!r}")
            errors += 1

    # Single source of truth contract (AGENTS.md § Source Of Truth):
    # commands must live in .opencode/commands/*.md exclusively. The
    # legacy opencode.json `command` block is forbidden here because
    # it creates a second source of truth.
    if cfg.get("command"):
        print(
            "[ERR] opencode.json must not contain a 'command' block — "
            "use .opencode/commands/*.md (AGENTS.md § Source Of Truth)"
        )
        errors += 1

    return errors


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _extract_frontmatter(text: str) -> str | None:
    m = _FRONTMATTER_RE.match(text)
    return m.group(1) if m else None


def _yaml_top_key(fm: str, key: str) -> str | None:
    """Return value of a top-level scalar or block-scalar `key:` line.

    Handles:
    - inline scalars (`key: value`)
    - single/double-quoted values (`key: "value"`, `key: 'value'`)
    - YAML block scalars (`key: |` or `key: >`, then indented lines).

    Returns the concatenated text content for block scalars. Returns
    None when the key is missing.
    """
    inline = re.compile(rf"^{re.escape(key)}:\s*(.*?)\s*$", re.MULTILINE)
    m = inline.search(fm)
    if not m:
        return None

    raw = m.group(1)
    if raw in ("|", ">", "|-", ">-", "|+", ">+"):
        # Block scalar: gather subsequent indented lines until a non-indented line.
        start = m.end()
        lines: list[str] = []
        for line in fm[start:].splitlines()[1:]:
            if not line.strip():
                lines.append("")
                continue
            if line[0] in (" ", "\t"):
                lines.append(line.lstrip())
            else:
                break
        text = " ".join(part for part in lines if part).strip()
        return text or None

    if raw == "":
        return None
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        raw = raw[1:-1]
    return raw


def validate_skill(skill_dir: Path) -> int:
    """Validate one skill directory."""
    name = skill_dir.name
    errors = 0

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        print(f"[ERR] {name}: missing SKILL.md")
        return 1

    if not re.match(r"^[a-z][a-z0-9-]{0,63}$", name):
        print(f"[ERR] {name}: name is not kebab-case or exceeds 64 chars")
        errors += 1

    text = skill_md.read_text(encoding="utf-8-sig")
    fm = _extract_frontmatter(text)
    if fm is None:
        print(f"[ERR] {name}: missing frontmatter delimiter")
        return errors + 1

    fm_name = _yaml_top_key(fm, "name")
    if fm_name is None:
        print(f"[ERR] {name}: missing frontmatter name")
        errors += 1
    elif fm_name != name:
        print(f"[ERR] {name}: frontmatter name {fm_name!r} != directory name")
        errors += 1

    description = _yaml_top_key(fm, "description")
    if not description:
        print(f"[ERR] {name}: missing frontmatter description")
        errors += 1
    elif not (1 <= len(description) <= 1024):
        print(f"[ERR] {name}: description length {len(description)} not in 1-1024")
        errors += 1

    if errors == 0:
        print(f"[OK] skill {name}")
    return errors


def validate_agent(agent_md: Path) -> int:
    """Validate one agent markdown file."""
    name = agent_md.stem
    text = agent_md.read_text(encoding="utf-8-sig")
    fm = _extract_frontmatter(text)

    if fm is None:
        print(f"[ERR] agent {name}: missing frontmatter delimiter")
        return 1

    errors = 0
    if not _yaml_top_key(fm, "description") and "description:" not in fm:
        print(f"[ERR] agent {name}: missing description")
        errors += 1

    mode = _yaml_top_key(fm, "mode")
    if mode and mode not in ("primary", "subagent"):
        print(f"[ERR] agent {name}: invalid mode {mode!r}")
        errors += 1

    color = _yaml_top_key(fm, "color")
    if color is not None:
        valid_named = {"primary", "secondary", "accent", "success", "warning", "error", "info"}
        if color not in valid_named and not re.match(r"^#[0-9a-fA-F]{6}$", color):
            print(f"[ERR] agent {name}: invalid color {color!r}")
            errors += 1

    if errors == 0:
        print(f"[OK] agent {name}")
    return errors


def validate_command(cmd_md: Path) -> int:
    """Validate one command markdown file."""
    name = cmd_md.stem
    text = cmd_md.read_text(encoding="utf-8-sig")
    fm = _extract_frontmatter(text)

    if fm is None:
        print(f"[ERR] command {name}: missing frontmatter delimiter")
        return 1

    if not _yaml_top_key(fm, "description"):
        print(f"[ERR] command {name}: missing description")
        return 1

    print(f"[OK] command {name}")
    return 0


def validate_version(path: Path) -> int:
    """Validate VERSION file as semver."""
    if not path.is_file():
        print(f"[ERR] VERSION file not found at {path}")
        return 1
    raw = path.read_text(encoding="utf-8-sig").strip()
    if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", raw):
        print(f"[ERR] VERSION {raw!r} not semver MAJOR.MINOR.PATCH")
        return 1
    print(f"[OK] VERSION {raw}")
    return 0


def main(argv: list[str]) -> int:
    """Entry point.

    Usage: _validate_helpers.py <command> <path> [<path>...]
    Commands: opencode_json | skill | agent | command | version
    """
    if len(argv) < 3:
        print("usage: _validate_helpers.py <command> <path> [<path>...]", file=sys.stderr)
        return 2

    cmd = argv[1]
    paths = [Path(p) for p in argv[2:]]

    dispatch = {
        "opencode_json": lambda p: validate_opencode_json(p),
        "skill": lambda p: validate_skill(p),
        "agent": lambda p: validate_agent(p),
        "command": lambda p: validate_command(p),
        "version": lambda p: validate_version(p),
    }
    if cmd not in dispatch:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2

    total = 0
    for p in paths:
        total += dispatch[cmd](p)
    return 1 if total > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
