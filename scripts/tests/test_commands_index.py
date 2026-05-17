"""Tests for `scripts/generate_commands_index.py` and the committed
`.opencode/commands/index.json` artifact. Mirror of `test_skills_index.py`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "generate_commands_index.py"
COMMANDS_DIR = REPO_ROOT / ".opencode" / "commands"
INDEX_PATH = COMMANDS_DIR / "index.json"
OPENCODE_JSON = REPO_ROOT / "opencode.json"
AGENTS_DIR = REPO_ROOT / ".opencode" / "agents"


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_index_exists() -> None:
    assert INDEX_PATH.exists(), "commands/index.json missing — regenerate via scripts/generate_commands_index.py"


def test_index_is_in_sync() -> None:
    result = _run(["--check"])
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"


def test_every_command_dir_in_index() -> None:
    on_disk = sorted(p.stem for p in COMMANDS_DIR.glob("*.md") if p.stem != "index")
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    indexed = sorted(c["name"] for c in index["commands"])
    assert on_disk == indexed, f"on disk: {on_disk}, indexed: {indexed}"


def test_every_command_targets_known_agent() -> None:
    """Every command.agent must resolve to a primary agent in opencode.json
    or a subagent in .opencode/agents/ or a built-in (build/plan/general/explore/scout).
    """
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    cfg = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    primary_agents = set(cfg.get("agent", {}).keys())
    subagents = {p.stem for p in AGENTS_DIR.glob("*.md")} if AGENTS_DIR.exists() else set()
    builtins = {"build", "plan", "general", "explore", "scout"}
    valid = primary_agents | subagents | builtins
    for cmd in index["commands"]:
        if cmd["agent"]:
            assert cmd["agent"] in valid, (
                f"command {cmd['name']!r} targets agent {cmd['agent']!r} which is unknown"
            )


def test_every_command_has_known_domain() -> None:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    valid_domains = {
        "flow", "serena", "rules", "explore", "browser",
        "design", "security", "lsp", "docs-sync",
    }
    for cmd in index["commands"]:
        assert cmd["domain"] in valid_domains, (
            f"command {cmd['name']!r} has invalid domain {cmd['domain']!r}; valid: {sorted(valid_domains)}"
        )


def test_count_matches_disk() -> None:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    on_disk = [p for p in COMMANDS_DIR.glob("*.md") if p.stem != "index"]
    assert index["count"] == len(on_disk)
