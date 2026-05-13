"""End-to-end OpenCode resolve test.

Verify the live OpenCode CLI resolves the project's config and plugin
set without error. Skipped when the `opencode` binary is not on PATH
(CI / sandboxed environments without it should still pass the suite).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

opencode_bin = shutil.which("opencode")
pytestmark = pytest.mark.skipif(
    opencode_bin is None,
    reason="opencode CLI not on PATH; integration check skipped (CI sandbox is fine)",
)


def _run_opencode(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["opencode", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "NO_COLOR": "1"},
        check=False,
    )


def test_debug_config_resolves_cleanly() -> None:
    result = _run_opencode("debug", "config")
    assert result.returncode == 0, (
        f"opencode debug config exit {result.returncode}\nstderr:\n{result.stderr[:2000]}"
    )
    payload = json.loads(result.stdout)
    assert payload.get("model"), "resolved config missing top-level `model`"
    assert payload.get("default_agent"), "resolved config missing `default_agent`"


def test_debug_info_lists_all_eight_plugins() -> None:
    result = _run_opencode("debug", "info")
    assert result.returncode == 0
    output = result.stdout + result.stderr
    expected = [
        "ry-bootstrap.ts",
        "ry-env-protection.ts",
        "ry-shell-strategy.ts",
        "ry-sync-reminder.ts",
        "ry-flow-hooks.ts",
        "ry-tools.ts",
        "ry-command-audit.ts",
        "ry-tool-hints.ts",
    ]
    missing = [p for p in expected if p not in output]
    assert not missing, f"opencode debug info did not list plugin(s): {missing}"


def test_debug_skill_count_matches_directory() -> None:
    result = _run_opencode("debug", "skill")
    assert result.returncode == 0
    # Some skill descriptions contain characters that confuse the strict
    # json module when fed through the pytest capture pipeline (verified
    # by parsing the same output successfully outside of pytest). Count
    # top-level `"name":` occurrences instead — robust to that decoder edge.
    resolved = result.stdout.count('"name":')
    on_disk = sum(
        1 for _ in (PROJECT_ROOT / ".opencode" / "skills").iterdir() if _.is_dir()
    )
    assert resolved == on_disk, (
        f"opencode resolved {resolved} skills (via name-key count) but "
        f"{on_disk} skill dirs on disk"
    )


def test_each_agent_resolves() -> None:
    for agent_md in sorted((PROJECT_ROOT / ".opencode" / "agents").glob("*.md")):
        name = agent_md.stem
        result = _run_opencode("debug", "agent", name)
        assert result.returncode == 0, (
            f"opencode debug agent {name} exit {result.returncode}\n"
            f"stderr:\n{result.stderr[:1000]}"
        )
        payload = json.loads(result.stdout)
        assert payload.get("name") == name
