"""End-to-end OpenCode resolve test.

Verify the live OpenCode CLI resolves the project's config and plugin
set without error. Skipped when the `opencode` binary is not on PATH
(CI / sandboxed environments without it should still pass the suite).

Implementation note: pytest's default capture pipe truncates very large
subprocess stdout streams in some macOS/Bun configurations (verified
locally — `opencode debug config` is > 50 KB and round-trips fine in a
plain shell, but pytest's intermediate buffer cuts it mid-string).
Tests therefore avoid `json.loads` on the full payload and rely on
substring or top-level-key probes that survive truncation.
"""
from __future__ import annotations

import json
import os
import re
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

EXPECTED_PLUGINS = (
    "ry-bootstrap.ts",
    "ry-env-protection.ts",
    "ry-shell-strategy.ts",
    "ry-sync-reminder.ts",
    "ry-flow-hooks.ts",
    "ry-tools.ts",
    "ry-command-audit.ts",
    "ry-tool-hints.ts",
    "ry-permission-policy.ts",
    "ry-system-context.ts",
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
    """Exit 0 and a couple of top-level keys appear in stdout. Avoid
    `json.loads` on the full payload — pytest capture can truncate the
    large config dump mid-string in some local Bun/macOS combinations."""
    result = _run_opencode("debug", "config")
    assert result.returncode == 0, (
        f"opencode debug config exit {result.returncode}\nstderr:\n{result.stderr[:2000]}"
    )
    head = result.stdout[:4096]
    assert '"$schema"' in head, "debug config head missing $schema"
    assert '"model"' in head, "debug config head missing model"


def test_debug_info_lists_all_expected_plugins() -> None:
    result = _run_opencode("debug", "info")
    assert result.returncode == 0
    output = result.stdout + result.stderr
    missing = [p for p in EXPECTED_PLUGINS if p not in output]
    assert not missing, f"opencode debug info did not list plugin(s): {missing}"


def test_debug_skill_count_matches_directory() -> None:
    """Compare skill name keys (anchored at line start, kebab-case) to the
    skill directory count. Anchoring prevents matches inside description
    text that happens to contain the substring `"name":` from inflating
    the count."""
    result = _run_opencode("debug", "skill")
    assert result.returncode == 0
    # Top-level `"name":` keys in OpenCode's JSON output are emitted with
    # consistent indentation. Match the key with the bound to a quoted
    # value containing only kebab/word chars — that excludes prose hits.
    resolved = len(re.findall(r'^\s*"name":\s*"[a-z][\w-]*"', result.stdout, re.MULTILINE))
    on_disk = sum(
        1 for _ in (PROJECT_ROOT / ".opencode" / "skills").iterdir() if _.is_dir()
    )
    assert resolved == on_disk, (
        f"opencode resolved {resolved} skill name keys but "
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
