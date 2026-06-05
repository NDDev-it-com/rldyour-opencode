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


def _expected_opencode_version() -> str:
    baseline = json.loads(
        (PROJECT_ROOT / "references" / "opencode-baseline.json").read_text(encoding="utf-8")
    )
    return baseline["baseline"]["opencode_cli"]["version"]


def _installed_opencode_version() -> str | None:
    if opencode_bin is None:
        return None
    proc = subprocess.run(
        ["opencode", "--version"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if proc.returncode != 0:
        return None
    match = re.search(r"\d+\.\d+\.\d+", proc.stdout + proc.stderr)
    return match.group(0) if match else None


opencode_bin = shutil.which("opencode")
expected_opencode_version = _expected_opencode_version()
installed_opencode_version = _installed_opencode_version()
pytestmark = pytest.mark.skipif(
    installed_opencode_version != expected_opencode_version,
    reason=(
        "opencode CLI is absent or not at the pinned baseline "
        f"{expected_opencode_version}; installed={installed_opencode_version!r}"
    ),
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
    "ry-permission-events.ts",
    "ry-system-context.ts",
)


def _run_opencode(*args: str) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["opencode", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=False,
        timeout=60,
        env={
            **os.environ,
            "NO_COLOR": "1",
            "NPM_CONFIG_PACKAGE_LOCK": "false",
            "npm_config_package_lock": "false",
        },
        check=False,
    )
    return subprocess.CompletedProcess(
        proc.args,
        proc.returncode,
        proc.stdout.decode("utf-8", errors="replace"),
        proc.stderr.decode("utf-8", errors="replace"),
    )


def test_debug_config_resolves_cleanly() -> None:
    """Exit 0 plus a handful of top-level keys appear early in stdout.
    Avoid `json.loads` on the full payload — pytest capture can truncate
    the large config dump mid-string in some local Bun/macOS combinations.

    `$schema` is the first key, `model` and `default_agent` sit after
    the `mcp` block (mcp can be ~3 KB on a 13-server marketplace so they
    appear after roughly 3 KB but before 4 KB). `compaction` lives after
    the larger `lsp` block and is NOT reliably in the first 4 KiB — so
    we do not assert on it here; `validate_config.sh` exercises the full
    file separately."""
    result = _run_opencode("debug", "config")
    assert result.returncode == 0, (
        f"opencode debug config exit {result.returncode}\nstderr:\n{result.stderr[:2000]}"
    )
    head = result.stdout[:4096]
    for key in ('"$schema"', '"model"', '"default_agent"'):
        assert key in head, f"debug config head missing {key}"


def test_debug_info_lists_all_expected_plugins() -> None:
    result = _run_opencode("debug", "info")
    assert result.returncode == 0
    output = result.stdout + result.stderr
    missing = [p for p in EXPECTED_PLUGINS if p not in output]
    assert not missing, f"opencode debug info did not list plugin(s): {missing}"


def test_debug_skill_resolves_cleanly() -> None:
    """Exit 0 plus at least one skill key in the head bytes.

    `opencode debug skill` emits ~140 KB of JSON. Pytest's default capture
    pipe truncates somewhere between 80 and 128 KB depending on the
    runner; counting `"name":` keys in the captured stdout therefore
    produces an undercount that is order-dependent (passes in a full
    suite, fails in isolation — confirmed). Switch to head-substring
    probes for the generic `"name"` and `"description"` keys; let
    `test_plugin_surface.py::test_all_expected_plugins_exist` +
    `validate_config.sh` enforce the actual skill count on disk.
    The runtime emits skills in registration order (NOT alphabetical),
    so any specific skill-name probe would be brittle."""
    result = _run_opencode("debug", "skill")
    assert result.returncode == 0
    head = result.stdout[:4096]
    for key in ('"name"', '"description"'):
        assert key in head, f"debug skill head missing {key} (skill discovery may be broken)"


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
