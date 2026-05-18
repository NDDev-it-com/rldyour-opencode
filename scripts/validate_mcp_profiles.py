#!/usr/bin/env python3
"""Validate references/mcp-profiles.json against opencode.json and the skill index.

Closes audit P1-3: the marketplace declares 13 MCP servers, and the docs
group them into profiles (base / research / browser / security / design /
repo). This validator turns the docs grouping into a machine-readable
contract:

- Every server in `opencode.json.mcp` belongs to exactly one profile.
- Every profile only references servers that exist in opencode.json.
- Every skill in `.opencode/skills/index.json` requires MCP servers that
  exist in opencode.json (mirrors `test_skills_index.py`, kept here so
  this validator is the single CI gate for the MCP graph).
- High-context servers (per `high_context.members`) used by any skill
  generate a soft warning so the operator notices the cost.

Exits 0 when the graph is clean. Exits 1 when any hard invariant fails.
Exits 2 on operational error (missing inputs).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILES_PATH = REPO_ROOT / "references" / "mcp-profiles.json"
OPENCODE_JSON = REPO_ROOT / "opencode.json"
SKILLS_INDEX = REPO_ROOT / ".opencode" / "skills" / "index.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        print(f"[ERR] required file missing: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERR] {path}: invalid JSON ({exc})", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict):
        print(f"[ERR] {path}: top-level must be an object", file=sys.stderr)
        sys.exit(2)
    return data


def _collect_problems(
    profiles: dict[str, Any],
    opencode: dict[str, Any],
    skills_index: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []

    declared_servers = set((opencode.get("mcp") or {}).keys())
    if not declared_servers:
        hard.append("opencode.json has no `mcp` section to validate against")
        return hard, soft

    profile_map = profiles.get("profiles") or {}
    if not isinstance(profile_map, dict) or not profile_map:
        hard.append("mcp-profiles.json must define a non-empty `profiles` object")
        return hard, soft

    seen: dict[str, str] = {}
    profile_members: dict[str, set[str]] = {}
    for profile_name, body in profile_map.items():
        members = (body or {}).get("members") or []
        if not isinstance(members, list):
            hard.append(f"profile {profile_name!r} `members` must be a list")
            continue
        profile_members[profile_name] = set(members)
        for server in members:
            if not isinstance(server, str):
                hard.append(f"profile {profile_name!r} contains non-string member {server!r}")
                continue
            if server in seen and seen[server] != profile_name:
                hard.append(
                    f"server {server!r} appears in multiple profiles: "
                    f"{seen[server]!r} and {profile_name!r}"
                )
            seen[server] = profile_name
            if server not in declared_servers:
                hard.append(
                    f"profile {profile_name!r} references server {server!r} "
                    f"that is not declared in opencode.json.mcp"
                )

    unmapped = sorted(declared_servers - set(seen.keys()))
    if unmapped:
        hard.append(
            f"servers declared in opencode.json.mcp but not assigned to any profile: "
            f"{unmapped}"
        )

    high_context_block = profiles.get("high_context") or {}
    high_context = set(high_context_block.get("members") or [])
    for server in high_context:
        if server not in declared_servers:
            hard.append(
                f"high_context member {server!r} is not declared in opencode.json.mcp"
            )

    if skills_index is None:
        soft.append(
            "skills/index.json not present; skipping skill.requires_mcp ⊆ opencode.mcp check"
        )
    else:
        for skill in skills_index.get("skills", []) or []:
            requires = skill.get("requires_mcp") or []
            for server in requires:
                if server not in declared_servers:
                    hard.append(
                        f"skill {skill.get('name')!r} requires MCP server {server!r} "
                        f"that is not declared in opencode.json.mcp"
                    )
                if server in high_context:
                    soft.append(
                        f"skill {skill.get('name')!r} pulls in high-context MCP "
                        f"{server!r}; confirm the dependency is justified"
                    )

    return hard, soft


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate MCP profile mappings + skill dependencies."
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=PROFILES_PATH,
        help=f"Path to mcp-profiles.json (default: {PROFILES_PATH.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--opencode",
        type=Path,
        default=OPENCODE_JSON,
        help=f"Path to opencode.json (default: {OPENCODE_JSON.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--skills-index",
        type=Path,
        default=SKILLS_INDEX,
        help=f"Path to skills index (default: {SKILLS_INDEX.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable envelope on stdout.",
    )
    args = parser.parse_args(argv)

    profiles = _load_json(args.profiles)
    opencode = _load_json(args.opencode)
    skills_index: dict[str, Any] | None
    if args.skills_index.exists():
        skills_index = _load_json(args.skills_index)
    else:
        skills_index = None

    hard, soft = _collect_problems(profiles, opencode, skills_index)

    def _display_path(p: Path) -> str:
        """Render a path relative to REPO_ROOT when the input is inside the
        repo; fall back to a plain string for fixture/temp paths so the
        validator works the same whether it is called from the live repo
        or from a test harness in `/tmp/...`."""
        try:
            return p.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return str(p)

    if args.json:
        envelope = {
            "profiles": _display_path(args.profiles),
            "opencode": _display_path(args.opencode),
            "skills_index": (
                _display_path(args.skills_index) if args.skills_index.exists() else None
            ),
            "problems": hard,
            "warnings": soft,
            "ok": not hard,
        }
        print(json.dumps(envelope, indent=2))
        return 0 if not hard else 1

    if hard:
        print(f"[FAIL] mcp profile graph: {len(hard)} hard problem(s):", file=sys.stderr)
        for problem in hard:
            print(f"  - {problem}", file=sys.stderr)
        if soft:
            print(f"[WARN] {len(soft)} soft warning(s):", file=sys.stderr)
            for warning in soft:
                print(f"  - {warning}", file=sys.stderr)
        return 1

    for warning in soft:
        print(f"[WARN] {warning}", file=sys.stderr)
    print(
        f"[OK] mcp profile graph consistent: "
        f"{len(set(profiles.get('profiles', {})))} profile(s) over "
        f"{len((opencode.get('mcp') or {}))} MCP server(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
