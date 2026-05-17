"""Tests for `scripts/generate_skills_index.py` and the committed
`.opencode/skills/index.json` artifact.

The index is the source of truth for skill-to-domain-to-MCP routing
consumed by external audits, sister marketplaces, and CI. These tests
keep the committed file synchronized with the SKILL.md files and with
`opencode.json` (so a renamed/removed MCP server can't leave a stale
requirement behind).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "generate_skills_index.py"
SKILLS_DIR = REPO_ROOT / ".opencode" / "skills"
INDEX_PATH = SKILLS_DIR / "index.json"
OPENCODE_JSON = REPO_ROOT / "opencode.json"


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_index_file_exists() -> None:
    assert INDEX_PATH.exists(), (
        "Skills index missing. Run: python3 scripts/generate_skills_index.py"
    )


def test_index_is_in_sync_with_skill_md_files() -> None:
    result = _run(["--check"])
    assert result.returncode == 0, (
        f"index.json out of sync. Regenerate via "
        f"python3 scripts/generate_skills_index.py\n{result.stderr}"
    )


def test_every_skill_dir_has_skill_md() -> None:
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith("."):
            continue
        skill_file = skill_dir / "SKILL.md"
        assert skill_file.exists(), f"{skill_dir.name} is missing SKILL.md"


def test_every_indexed_skill_has_required_mcp_declared() -> None:
    """If a skill declares a MCP requirement, that MCP must exist in opencode.json."""
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    cfg = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    available = set(cfg.get("mcp", {}).keys())
    for skill in index["skills"]:
        for server in skill["requires_mcp"]:
            assert server in available, (
                f"skill {skill['name']!r} requires MCP {server!r} not declared in opencode.json. "
                f"Update DOMAIN_BY_SKILL / REQUIRES_MCP in generate_skills_index.py."
            )


def test_every_skill_has_a_known_domain() -> None:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    valid_domains = {
        "flow", "serena", "rules", "explore", "browser",
        "design", "security", "lsp", "docs-sync",
    }
    for skill in index["skills"]:
        assert skill["domain"] in valid_domains, (
            f"skill {skill['name']!r} has invalid domain {skill['domain']!r}; "
            f"valid domains: {sorted(valid_domains)}"
        )


def test_count_matches_committed_skill_dirs() -> None:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    on_disk = [d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
    assert index["count"] == len(on_disk), (
        f"index says {index['count']} but {len(on_disk)} SKILL.md files exist on disk"
    )
