#!/usr/bin/env python3
"""Generate `.opencode/commands/index.json` — a machine-readable map of every
slash-command frontmatter + curated metadata (domain, expected agent).

Companion to `scripts/generate_skills_index.py`. Same pattern, same `--check`
contract: the index is generated, not human-authored, and the test asserts
it stays in sync with the SKILL/command files on disk.

The index lets external audits and sister marketplaces consume the
command-to-domain-to-agent routing contract without parsing 10 markdown
frontmatter blocks. CI verifies that the committed index matches the
generator output, so a renamed agent or removed command surfaces as a
test failure rather than silent drift.

Source of truth: the command markdown frontmatter (`description`, `agent`,
optional `subtask`) is authoritative for fields it exposes. Curated fields
(`domain`, `triggers`) live in this script and must be updated when new
commands are added.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = REPO_ROOT / ".opencode" / "commands"
INDEX_PATH = COMMANDS_DIR / "index.json"
OPENCODE_JSON = REPO_ROOT / "opencode.json"
AGENTS_DIR = REPO_ROOT / ".opencode" / "agents"

# Curated metadata: each command belongs to exactly one domain
# (see AGENTS.md § Domain Boundaries). `triggers` are short user-intent
# phrases used by the auto-routing layer.
COMMAND_METADATA: dict[str, dict[str, Any]] = {
    "ry-init": {
        "domain": "flow",
        "triggers": ["init project", "context pack", "study repo", "scope discovery"],
    },
    "ry-start": {
        "domain": "flow",
        "triggers": ["full SDLC", "ship feature", "implement task", "build feature"],
    },
    "ry-review": {
        "domain": "flow",
        "triggers": ["review diff", "review PR", "report-only review", "audit changes"],
    },
    "ry-newp": {
        "domain": "flow",
        "triggers": ["new project", "design from brief", "architecture docs"],
    },
    "ry-deploy": {
        "domain": "flow",
        "triggers": ["deploy", "release to server", "fix-forward"],
    },
    "ry-sync": {
        "domain": "flow",
        "triggers": ["finalize task", "post-task sync", "publish fullrepo"],
    },
    "ry-design": {
        "domain": "design",
        "triggers": ["Figma to code", "build UI", "design workflow", "redesign"],
    },
    "ry-explore": {
        "domain": "explore",
        "triggers": ["deep research", "library lookup", "tech investigation"],
    },
    "ry-sec-review": {
        "domain": "security",
        "triggers": ["security review", "OWASP audit", "defensive review"],
    },
    "ry-rules-review": {
        "domain": "rules",
        "triggers": ["rules audit", "report-only review", "check rldyour rules"],
    },
}


def parse_command(command_path: Path) -> dict[str, Any]:
    """Parse <name>.md frontmatter."""
    text = command_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{command_path}: missing YAML frontmatter")
    end = text.find("\n---", 3)
    if end < 0:
        raise ValueError(f"{command_path}: unterminated YAML frontmatter")
    raw_frontmatter = text[3:end].strip()
    frontmatter = yaml.safe_load(raw_frontmatter)
    if not isinstance(frontmatter, dict):
        raise ValueError(f"{command_path}: frontmatter root must be a mapping")
    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        description = str(description)
    agent = frontmatter.get("agent", "")
    if not isinstance(agent, str):
        agent = str(agent)
    subtask = bool(frontmatter.get("subtask", False))
    return {
        "name": command_path.stem,
        "description": description,
        "agent": agent,
        "subtask": subtask,
    }


def build_index() -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    for command_path in sorted(COMMANDS_DIR.glob("*.md")):
        if command_path.name == "index.json":
            continue
        parsed = parse_command(command_path)
        slug = parsed["name"]
        metadata = COMMAND_METADATA.get(slug, {})
        relative_path = command_path.relative_to(REPO_ROOT).as_posix()
        commands.append(
            {
                "name": parsed["name"],
                "path": relative_path,
                "description": parsed["description"],
                "agent": parsed["agent"],
                "subtask": parsed["subtask"],
                "domain": metadata.get("domain", "unknown"),
                "triggers": metadata.get("triggers", []),
            },
        )
    return {
        "version": "1.0.0",
        "generated_by": "scripts/generate_commands_index.py",
        "count": len(commands),
        "commands": commands,
    }


def _verify(index: dict[str, Any]) -> list[str]:
    """Structural verification against opencode.json and .opencode/agents/."""
    problems: list[str] = []
    try:
        cfg = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read opencode.json: {exc}"]
    agent_block = cfg.get("agent", {}) if isinstance(cfg, dict) else {}
    primary_agents = set(agent_block.keys()) if isinstance(agent_block, dict) else set()
    subagents = {p.stem for p in AGENTS_DIR.glob("*.md")} if AGENTS_DIR.exists() else set()
    all_agents = primary_agents | subagents | {"build", "plan", "general", "explore", "scout"}
    for cmd in index["commands"]:
        if cmd["agent"] and cmd["agent"] not in all_agents:
            problems.append(
                f"command {cmd['name']!r} targets agent {cmd['agent']!r} which is neither in "
                f"opencode.json.agent nor in .opencode/agents/ nor a built-in"
            )
        if cmd["domain"] == "unknown":
            problems.append(f"command {cmd['name']!r} has no domain in COMMAND_METADATA")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify .opencode/commands/index.json")
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
                "[FAIL] .opencode/commands/index.json is out of sync with the .md files.\n"
                "Regenerate via: python3 scripts/generate_commands_index.py",
                file=sys.stderr,
            )
            return 1
        if structural and args.strict:
            for problem in structural:
                print(f"[FAIL] {problem}", file=sys.stderr)
            return 1
        for problem in structural:
            print(f"[WARN] {problem}", file=sys.stderr)
        print(f"[OK] {INDEX_PATH.name}: {index['count']} commands, in sync")
        return 0

    INDEX_PATH.write_text(rendered, encoding="utf-8")
    print(f"[OK] wrote {INDEX_PATH.relative_to(REPO_ROOT)} ({index['count']} commands)")
    for problem in structural:
        print(f"[WARN] {problem}", file=sys.stderr)
    if structural and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
