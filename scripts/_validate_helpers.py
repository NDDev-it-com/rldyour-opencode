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

try:
    import yaml
except ImportError as _exc:  # pragma: no cover - tooling boundary
    print(
        "[ERR] PyYAML is required for fail-closed frontmatter validation. "
        "Install via `pip install PyYAML` (CI uses pinned PyYAML==6.0.3).",
        file=sys.stderr,
    )
    raise SystemExit(2) from _exc

# v1.15.3 canonical permission key set sourced from the built-in
# `customize-opencode` skill (`opencode debug skill` -> the `<built-in>`
# entry) and cross-validated against the v1.15.3 JSON Schema published
# at https://opencode.ai/config.json. Unknown keys are silently accepted
# by the runtime today (issue sst/opencode#15507), so this validator is
# the project-side defense against PascalCase typos and stale keys
# (notably `codesearch`, which was removed between v1.14.48 and v1.15.3).
CANONICAL_PERMISSION_KEYS: frozenset[str] = frozenset(
    {
        "read",
        "edit",
        "glob",
        "grep",
        "list",
        "bash",
        "task",
        "external_directory",
        "todowrite",
        "question",
        "webfetch",
        "websearch",
        "repo_clone",
        "repo_overview",
        "lsp",
        "doom_loop",
        "skill",
    }
)


def _check_permission_block(label: str, perm: object) -> int:
    """Validate a single `permission` block.

    A permission block is either:
    - a string action (`"allow"` / `"ask"` / `"deny"`), or
    - an object mapping known permission keys to actions or per-pattern
      action objects.

    Returns the number of errors found and prints `[ERR]` lines for each.
    """
    if isinstance(perm, str):
        # String form: "allow" / "ask" / "deny". Validated as a value
        # action elsewhere; here we only care about per-key validation
        # which doesn't apply to the string form.
        return 0
    if perm is None:
        return 0
    if not isinstance(perm, dict):
        print(f"[ERR] {label}: permission must be a string or object, got {type(perm).__name__}")
        return 1

    errors = 0
    for key in perm:
        if key not in CANONICAL_PERMISSION_KEYS:
            sorted_canon = ", ".join(sorted(CANONICAL_PERMISSION_KEYS))
            print(
                f"[ERR] {label}: unknown permission key {key!r} "
                f"(canonical set for v1.15.x: {sorted_canon})"
            )
            errors += 1
    return errors


def validate_opencode_json(path: Path) -> int:
    """Validate top-level opencode.json shape."""
    errors = 0
    try:
        cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        print(f"[ERR] {path}: file not found")
        return 1
    except json.JSONDecodeError as exc:
        print(f"[ERR] {path}: JSON decode error: {exc}")
        return 1

    if "model" not in cfg:
        print("[ERR] Missing required top-level key: model")
        errors += 1
    else:
        print(f"[OK] Top-level key present: model = {cfg['model']}")

    # Top-level permission block.
    errors += _check_permission_block("opencode.json.permission", cfg.get("permission"))

    for name, agent in (cfg.get("agent") or {}).items():
        mode = agent.get("mode")
        if mode and mode not in ("primary", "subagent", "all"):
            print(f"[ERR] Agent {name!r}: invalid mode: {mode!r}")
            errors += 1

        agent_perm = agent.get("permission")
        edit = (agent_perm or {}).get("edit") if isinstance(agent_perm, dict) else None
        if isinstance(edit, str) and edit not in ("allow", "ask", "deny"):
            print(f"[ERR] Agent {name!r}: invalid edit permission: {edit!r}")
            errors += 1

        errors += _check_permission_block(f"opencode.json.agent.{name}.permission", agent_perm)

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

    if errors == 0 and (cfg.get("permission") or cfg.get("agent")):
        print(
            f"[OK] Permission keys conform to v1.15.x canonical set "
            f"({len(CANONICAL_PERMISSION_KEYS)} keys)"
        )

    return errors


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _extract_frontmatter(text: str) -> str | None:
    m = _FRONTMATTER_RE.match(text)
    return m.group(1) if m else None


class DuplicateYamlKey(ValueError):
    """Raised when a frontmatter has the same top-level key more than once."""


def _parse_frontmatter_yaml(fm: str, label: str) -> tuple[dict[str, object] | None, int]:
    """Parse YAML frontmatter strictly via yaml.safe_load.

    Returns (parsed_dict, errors). `parsed_dict` is None on parse failure.
    Reports duplicate top-level keys (silent ambiguity in regex parser).
    Strict YAML parsing rejects unquoted descriptions that contain a second
    colon (e.g. `description: Orchestrated review: notes`) — exactly the
    failure mode silently allowed by the legacy regex parser.
    """
    try:
        data = yaml.safe_load(fm)
    except yaml.YAMLError as exc:
        print(f"[ERR] {label}: YAML parse error: {exc}")
        return None, 1

    if data is None:
        print(f"[ERR] {label}: empty frontmatter")
        return None, 1
    if not isinstance(data, dict):
        print(f"[ERR] {label}: frontmatter root must be a mapping, got {type(data).__name__}")
        return None, 1

    errors = 0
    seen: set[str] = set()
    for line in fm.splitlines():
        m = re.match(r"^([\w-]+):", line)
        if m:
            key = m.group(1)
            if key in seen:
                print(f"[ERR] {label}: duplicate top-level key {key!r}")
                errors += 1
            seen.add(key)

    return data, errors


def _yaml_top_key(fm: str, key: str) -> str | None:
    """Return value of a top-level scalar or block-scalar `key:` line.

    Handles:
    - inline scalars (`key: value`)
    - single/double-quoted values (`key: "value"`, `key: 'value'`)
    - YAML block scalars (`key: |` or `key: >`, then indented lines).

    Returns the concatenated text content for block scalars. Returns
    None when the key is missing. Raises DuplicateYamlKey if the key
    appears more than once at column 0 — YAML forbids duplicate keys
    and a regex parser cannot disambiguate which value is authoritative.
    """
    # `\s` matches \n, so `\s*$` could eat the line break and slide into
    # the next line — making `description:\nmode: subagent` return
    # "mode: subagent". Constrain to non-newline whitespace.
    inline = re.compile(rf"^{re.escape(key)}:[^\S\n]*(.*?)[^\S\n]*$", re.MULTILINE)
    matches = list(inline.finditer(fm))
    if not matches:
        return None
    if len(matches) > 1:
        raise DuplicateYamlKey(f"duplicate top-level key {key!r}")
    m = matches[0]

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


def _yaml_block_child_keys(fm: str, parent_key: str) -> list[str]:
    """Return the list of direct child keys under a YAML block mapping.

    Example:
        permission:
          edit: allow
          bash:
            "*": ask
            git diff: allow

    For `parent_key="permission"` returns `["edit", "bash"]` (not nested
    keys like `git diff`). Returns empty list if the parent key is
    missing or has no block children. Regex-only — does not require
    a full YAML parser.

    Implementation note: the parent line is matched with `permission:`
    at column 0, then we scan subsequent lines and accept ones that are
    indented by exactly the same amount and have a `:` separator after
    the key. Deeper nesting and quoted-key lines are ignored.
    """
    parent_re = re.compile(rf"^{re.escape(parent_key)}:[^\S\n]*$", re.MULTILINE)
    m = parent_re.search(fm)
    if not m:
        return []

    start = m.end()
    body = fm[start:].lstrip("\n")
    lines = body.splitlines()

    keys: list[str] = []
    child_indent: int | None = None
    for line in lines:
        if not line.strip():
            # blank line still allows the block to continue
            continue
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if indent == 0:
            # back to the same level as `parent_key:` — block ended
            break
        if child_indent is None:
            child_indent = indent
        if indent != child_indent:
            # deeper-nested line — belongs to a child block, skip
            continue
        # accept `key:` or `"key":` or `'key':` at exactly `child_indent`
        key_match = re.match(r"""^(?:"([^"]+)"|'([^']+)'|([\w-]+))\s*:""", stripped)
        if key_match:
            key = key_match.group(1) or key_match.group(2) or key_match.group(3)
            keys.append(key)
    return keys


def validate_skill(skill_dir: Path) -> int:
    """Validate one skill directory via strict YAML parse."""
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

    data, parse_errors = _parse_frontmatter_yaml(fm, f"skill {name}")
    errors += parse_errors
    if data is None:
        return errors

    fm_name = data.get("name")
    description = data.get("description")

    if fm_name is None:
        print(f"[ERR] {name}: missing frontmatter name")
        errors += 1
    elif not isinstance(fm_name, str):
        print(f"[ERR] {name}: frontmatter name must be a string, got {type(fm_name).__name__}")
        errors += 1
    elif fm_name != name:
        print(f"[ERR] {name}: frontmatter name {fm_name!r} != directory name")
        errors += 1

    if not description:
        print(f"[ERR] {name}: missing frontmatter description")
        errors += 1
    elif not isinstance(description, str):
        print(f"[ERR] {name}: description must be a string, got {type(description).__name__}")
        errors += 1
    elif not (1 <= len(description) <= 1024):
        print(f"[ERR] {name}: description length {len(description)} not in 1-1024")
        errors += 1

    # Forbidden Claude Code / Codex residue fields per AGENTS.md skill rules.
    forbidden_skill_fields = {
        "allowed-tools",
        "disable-model-invocation",
        "model",
        "effort",
        "maxTurns",
        "paths",
        "context",
        "agent",
    }
    for forbidden in forbidden_skill_fields:
        if forbidden in data:
            print(
                f"[ERR] {name}: forbidden skill frontmatter field {forbidden!r} "
                "(Claude Code / Codex residue; not honoured by OpenCode)"
            )
            errors += 1

    if errors == 0:
        print(f"[OK] skill {name}")
    return errors


def validate_agent(agent_md: Path) -> int:
    """Validate one agent markdown file via strict YAML parse."""
    name = agent_md.stem
    text = agent_md.read_text(encoding="utf-8-sig")
    fm = _extract_frontmatter(text)

    if fm is None:
        print(f"[ERR] agent {name}: missing frontmatter delimiter")
        return 1

    data, errors = _parse_frontmatter_yaml(fm, f"agent {name}")
    if data is None:
        return errors

    description = data.get("description")
    mode = data.get("mode")
    color = data.get("color")
    agent_perm = data.get("permission")

    if not description:
        print(f"[ERR] agent {name}: missing description")
        errors += 1
    elif not isinstance(description, str):
        print(f"[ERR] agent {name}: description must be a string, got {type(description).__name__}")
        errors += 1
    elif not (1 <= len(description) <= 1024):
        print(f"[ERR] agent {name}: description length {len(description)} not in 1-1024")
        errors += 1

    # OpenCode v1.15.x supports mode: primary | subagent | all (default all).
    # https://opencode.ai/docs/agents
    if mode is not None and mode not in ("primary", "subagent", "all"):
        print(f"[ERR] agent {name}: invalid mode {mode!r} (expected primary | subagent | all)")
        errors += 1

    if color is not None:
        valid_named = {"primary", "secondary", "accent", "success", "warning", "error", "info"}
        if not isinstance(color, str):
            print(f"[ERR] agent {name}: color must be a string, got {type(color).__name__}")
            errors += 1
        elif color not in valid_named and not re.match(r"^#[0-9a-fA-F]{6}$", color):
            print(f"[ERR] agent {name}: invalid color {color!r}")
            errors += 1

    # Permission keys must come from the v1.15.x canonical set.
    # Stale keys (notably `codesearch`, removed between v1.14.48 and
    # v1.15.3) and PascalCase typos are accepted silently by the runtime
    # (issue sst/opencode#15507), so project validation is the only line
    # of defense.
    if isinstance(agent_perm, dict):
        for key in agent_perm.keys():
            if not isinstance(key, str) or key not in CANONICAL_PERMISSION_KEYS:
                sorted_canon = ", ".join(sorted(CANONICAL_PERMISSION_KEYS))
                print(
                    f"[ERR] agent {name}: unknown permission key {key!r} "
                    f"(canonical set for v1.15.x: {sorted_canon})"
                )
                errors += 1

    if errors == 0:
        print(f"[OK] agent {name}")
    return errors


def validate_command(cmd_md: Path) -> int:
    """Validate one command markdown file via strict YAML parse."""
    name = cmd_md.stem
    text = cmd_md.read_text(encoding="utf-8-sig")
    fm = _extract_frontmatter(text)

    if fm is None:
        print(f"[ERR] command {name}: missing frontmatter delimiter")
        return 1

    data, errors = _parse_frontmatter_yaml(fm, f"command {name}")
    if data is None:
        return errors

    description = data.get("description")
    if not description:
        print(f"[ERR] command {name}: missing description")
        return errors + 1
    if not isinstance(description, str):
        print(f"[ERR] command {name}: description must be a string, got {type(description).__name__}")
        return errors + 1

    if errors == 0:
        print(f"[OK] command {name}")
    return errors


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
