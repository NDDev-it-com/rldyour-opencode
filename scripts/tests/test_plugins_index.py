"""Tests for `scripts/generate_plugins_index.py` and the committed
`.opencode/plugins/index.json` artifact. Mirror of `test_skills_index.py`
and `test_commands_index.py`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "generate_plugins_index.py"
PLUGINS_DIR = REPO_ROOT / ".opencode" / "plugins"
INDEX_PATH = PLUGINS_DIR / "index.json"

VALID_CATEGORIES = {
    "lifecycle",
    "observability",
    "guardrail",
    "advisory",
    "context-injection",
    "routing",
    "tool-registration",
}


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
    assert INDEX_PATH.exists(), "plugins/index.json missing — regenerate via scripts/generate_plugins_index.py"


def test_index_is_in_sync() -> None:
    result = _run(["--check"])
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"


def test_every_plugin_file_in_index() -> None:
    on_disk = sorted(p.stem for p in PLUGINS_DIR.glob("*.ts"))
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    indexed = sorted(p["name"] for p in index["plugins"])
    assert on_disk == indexed


def test_every_plugin_has_known_category() -> None:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    for plugin in index["plugins"]:
        assert plugin["category"] in VALID_CATEGORIES, (
            f"plugin {plugin['name']!r} has invalid category {plugin['category']!r}; valid: {sorted(VALID_CATEGORIES)}"
        )


def test_every_plugin_subscribes_to_at_least_one_hook() -> None:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    for plugin in index["plugins"]:
        assert plugin["hooks"], (
            f"plugin {plugin['name']!r} has no hooks — index generator may have lost a pattern, "
            f"or the plugin no longer subscribes to anything. Run "
            f"scripts/generate_plugins_index.py to refresh and inspect."
        )


def test_defense_in_depth_pair_is_bidirectional() -> None:
    """If plugin A names B in defense_in_depth_pair, B must name A back.
    The Phase 1 hardening locked this invariant for ry-shell-strategy +
    ry-permission-policy; the index reflects it.
    """
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    by_name = {p["name"]: p for p in index["plugins"]}
    for plugin in index["plugins"]:
        pair = plugin.get("defense_in_depth_pair")
        if not pair:
            continue
        assert pair in by_name, f"plugin {plugin['name']!r} pairs with unknown {pair!r}"
        reverse = by_name[pair].get("defense_in_depth_pair")
        assert reverse == plugin["name"], (
            f"defense_in_depth_pair asymmetry: {plugin['name']!r}→{pair!r} but "
            f"{pair!r}→{reverse!r} (expected {plugin['name']!r})"
        )


def test_count_matches_disk() -> None:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    on_disk = list(PLUGINS_DIR.glob("*.ts"))
    assert index["count"] == len(on_disk)
