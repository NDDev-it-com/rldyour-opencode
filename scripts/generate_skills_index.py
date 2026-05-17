#!/usr/bin/env python3
"""Generate `.opencode/skills/index.json` — a machine-readable map of every
SKILL.md frontmatter + curated metadata (domain, requires_mcp, network).

The OpenCode runtime discovers `.opencode/skills/<name>/SKILL.md` files
directly, so this index is NOT a runtime artifact. It exists to:

  1. Let CI verify that every skill referenced in the marketplace has the
     MCP servers it claims to need actually present in `opencode.json.mcp`.
  2. Let CI assert that every skill belongs to exactly one declared domain
     (the AGENTS.md § Domain Boundaries contract).
  3. Give external tools (sister marketplaces, audit scripts) a single
     source of truth for skill-to-domain-to-MCP routing.

Run with `--check` in CI to fail when the generated content diverges from
the committed `index.json` — this prevents silent drift between SKILL.md
files and the index.

Source of truth: the SKILL.md frontmatter (`name`, `description`) is
authoritative for fields it exposes. Curated fields (domain, requires_mcp,
network) live in this script and must be updated when new skills are added.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / ".opencode" / "skills"
INDEX_PATH = SKILLS_DIR / "index.json"
OPENCODE_JSON = REPO_ROOT / "opencode.json"

# Curated metadata: each skill belongs to exactly one domain
# (see AGENTS.md § Domain Boundaries). `requires_mcp` lists OpenCode MCP
# server names the skill consumes; `network` is true when the skill uses
# remote MCP or web fetch as part of its happy path.
DOMAIN_BY_SKILL: dict[str, str] = {
    # Flow (6)
    "flow-post-task-sync": "flow",
    "ry-init": "flow",
    "ry-start": "flow",
    "ry-review": "flow",
    "ry-newp": "flow",
    "ry-deploy": "flow",
    # Serena (3)
    "serena-code-workflow": "serena",
    "serena-memory-sync": "serena",
    "serena-lsp-integration": "serena",
    # Rules (7)
    "quality-first-engineering": "rules",
    "architecture-boundaries": "rules",
    "implementation-discipline": "rules",
    "dependency-compatibility-policy": "rules",
    "verification-quality-gates": "rules",
    "project-instructions-policy": "rules",
    "ry-rules-review": "rules",
    # Explore (2)
    "tech-research": "explore",
    "web-research": "explore",
    # Browser (3)
    "browser-tool-routing": "browser",
    "browser-validation": "browser",
    "browser-debug": "browser",
    # Design (5)
    "ry-design": "design",
    "figma-to-code": "design",
    "design-system-implementation": "design",
    "fsd-frontend-architecture": "design",
    "design-validation": "design",
    # Security (2)
    "owasp-top-10-implementation": "security",
    "ry-sec-review": "security",
    # LSP (3)
    "lsp-routing": "lsp",
    "lsp-health-check": "lsp",
    "lsp-setup": "lsp",
    # Docs sync (1)
    "instruction-docs-sync": "docs-sync",
}

# Per-skill MCP dependencies. Skills not listed here have no required MCP.
REQUIRES_MCP: dict[str, list[str]] = {
    "serena-code-workflow": ["serena"],
    "serena-memory-sync": ["serena"],
    "serena-lsp-integration": ["serena"],
    "browser-tool-routing": ["playwright", "chrome-devtools"],
    "browser-validation": ["playwright", "chrome-devtools"],
    "browser-debug": ["chrome-devtools"],
    "ry-design": ["figma", "shadcn", "playwright", "chrome-devtools"],
    "figma-to-code": ["figma", "shadcn"],
    "design-system-implementation": ["shadcn"],
    "design-validation": ["playwright", "chrome-devtools"],
    "owasp-top-10-implementation": ["semgrep"],
    "ry-sec-review": ["semgrep"],
    "tech-research": ["context7", "deepwiki", "grep"],
    "web-research": [],
    "ry-init": ["serena"],
    "ry-start": ["serena", "sequential-thinking"],
    "ry-review": ["serena"],
    "ry-newp": ["context7", "deepwiki", "grep", "sequential-thinking"],
    "ry-deploy": [],
}

# Skills that intentionally touch the network as part of their core workflow.
NETWORK_SKILLS = {
    "tech-research",
    "web-research",
    "browser-validation",
    "browser-debug",
    "browser-tool-routing",
    "figma-to-code",
    "ry-design",
    "design-validation",
    "owasp-top-10-implementation",
    "ry-sec-review",
    "ry-newp",
}

_TRIGGERS_RE = re.compile(r"EN triggers?:\s*(.+?)(?:\.|\Z)", re.IGNORECASE | re.DOTALL)


def _split_triggers(raw: str) -> list[str]:
    """Best-effort split of `EN triggers: foo, bar, baz` text."""
    parts: list[str] = []
    for fragment in raw.split(","):
        cleaned = fragment.strip()
        if cleaned:
            parts.append(cleaned)
    return parts


def parse_skill(skill_path: Path) -> dict[str, Any]:
    """Parse SKILL.md frontmatter and EN triggers."""
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{skill_path}: missing YAML frontmatter")
    end = text.find("\n---", 3)
    if end < 0:
        raise ValueError(f"{skill_path}: unterminated YAML frontmatter")
    raw_frontmatter = text[3:end].strip()
    frontmatter = yaml.safe_load(raw_frontmatter)
    if not isinstance(frontmatter, dict):
        raise ValueError(f"{skill_path}: frontmatter root must be a mapping")
    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        description = str(description)
    triggers_match = _TRIGGERS_RE.search(description)
    triggers = _split_triggers(triggers_match.group(1)) if triggers_match else []
    return {
        "name": frontmatter.get("name") or skill_path.parent.name,
        "description": description,
        "triggers": triggers,
    }


def build_index() -> dict[str, Any]:
    skills: list[dict[str, Any]] = []
    discovered: list[str] = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        slug = skill_dir.name
        discovered.append(slug)
        parsed = parse_skill(skill_file)
        relative_path = skill_file.relative_to(REPO_ROOT).as_posix()
        skills.append(
            {
                "name": parsed["name"],
                "path": relative_path,
                "domain": DOMAIN_BY_SKILL.get(slug, "unknown"),
                "triggers": parsed["triggers"],
                "requires_mcp": REQUIRES_MCP.get(slug, []),
                "network": slug in NETWORK_SKILLS,
            },
        )
    return {
        "version": 1,
        "generated_by": "scripts/generate_skills_index.py",
        "count": len(skills),
        "skills": skills,
    }


def _verify_against_opencode_json(index: dict[str, Any]) -> list[str]:
    """Return a list of structural problems with the generated index."""
    problems: list[str] = []
    try:
        cfg = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read opencode.json: {exc}"]
    mcp = cfg.get("mcp", {}) if isinstance(cfg, dict) else {}
    available_mcp = set(mcp.keys()) if isinstance(mcp, dict) else set()
    for skill in index["skills"]:
        for server in skill["requires_mcp"]:
            if server not in available_mcp:
                problems.append(
                    f"skill {skill['name']!r} requires MCP {server!r} not declared in opencode.json"
                )
        if skill["domain"] == "unknown":
            problems.append(f"skill {skill['name']!r} has no domain assignment in DOMAIN_BY_SKILL")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify .opencode/skills/index.json")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed index matches the generated content; exit 1 if it drifts.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat structural problems (unknown domain, missing MCP) as fatal.",
    )
    args = parser.parse_args(argv)

    index = build_index()
    rendered = json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    structural = _verify_against_opencode_json(index)

    if args.check:
        committed = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""
        if committed != rendered:
            print(
                "[FAIL] .opencode/skills/index.json is out of sync with the SKILL.md files.\n"
                "Regenerate via: python3 scripts/generate_skills_index.py",
                file=sys.stderr,
            )
            return 1
        if structural and args.strict:
            for problem in structural:
                print(f"[FAIL] {problem}", file=sys.stderr)
            return 1
        if structural:
            for problem in structural:
                print(f"[WARN] {problem}", file=sys.stderr)
        print(f"[OK] {INDEX_PATH.name}: {index['count']} skills, in sync")
        return 0

    INDEX_PATH.write_text(rendered, encoding="utf-8")
    print(f"[OK] wrote {INDEX_PATH.relative_to(REPO_ROOT)} ({index['count']} skills)")
    if structural:
        for problem in structural:
            print(f"[WARN] {problem}", file=sys.stderr)
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
