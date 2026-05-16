"""Integration tests for scripts/doctor_opencode.sh.

The doctor script is a thin diagnostic wrapper around `opencode.json`,
the agent/skill/command directories, and `.git/info/exclude`. The risk
surface that broke between v0.10.0 and v0.10.1 was two false-positive
WARN lines:

1. The LSP-enabled check compared `cfg.get("lsp", False)` (a dict in
   the project config) against the string "True" — always false,
   producing a stale "LSP not enabled" WARN even though the v1.15.x
   runtime fully accepts the object form.
2. The exclude-marker check grepped for the legacy
   `rldyour-opencode agent-only files` string, which the
   `scripts/fullrepo_sync.py` bootstrap intentionally removed in favor
   of a canonical `>>> rldyour fullrepo agent-only files >>>` block.

These tests guard both behaviors against regression. They run the real
script against the live repo (read-only — the script never writes), so
they also smoke-check that python3 + grep + the LSP catalog all stay
healthy enough for an operator triage session.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCTOR = REPO_ROOT / "scripts" / "doctor_opencode.sh"


def _ansi_strip(text: str) -> str:
    """Strip ANSI color codes from doctor output for stable assertions."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


@pytest.fixture(scope="module")
def doctor_output() -> str:
    """Run the doctor once per module — fast and idempotent."""
    proc = subprocess.run(
        ["bash", str(DOCTOR)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "TERM": "dumb"},
    )
    # Exit 0 is required: a real ERR would mean the project state itself is broken.
    assert proc.returncode == 0, f"doctor exit={proc.returncode} stderr={proc.stderr[:500]}"
    return _ansi_strip(proc.stdout)


def test_doctor_exits_clean(doctor_output: str) -> None:
    assert "No issues found" in doctor_output


def test_doctor_lsp_enabled_with_object_form(doctor_output: str) -> None:
    """opencode.json sets `lsp` as an object — doctor must recognize that as enabled."""
    assert re.search(r"\[OK\]\s+LSP enabled", doctor_output) is not None, doctor_output
    # Regression guard: the stale "LSP not enabled" WARN string must NOT appear.
    assert "LSP not enabled" not in doctor_output


def test_doctor_lsp_reports_custom_server_count(doctor_output: str) -> None:
    """When `lsp` is an object, doctor reports `N custom server(s) on top of built-ins`."""
    m = re.search(r"LSP enabled \((\d+) custom server\(s\)", doctor_output)
    assert m is not None, doctor_output
    # The project ships 8 custom servers (ruff, vscode-html, vscode-css, vscode-json,
    # docker, taplo, marksman, qmlls). If the count drifts, AGENTS.md and references
    # need a coordinated update.
    assert int(m.group(1)) >= 1


def test_doctor_exclude_marker_matches_fullrepo_block(doctor_output: str) -> None:
    """The fullrepo block is the canonical marker; legacy bootstrap marker is fallback."""
    assert (
        "Agent-only exclude patterns installed (fullrepo block)" in doctor_output
        or "Agent-only exclude patterns installed (legacy bootstrap block)" in doctor_output
    ), doctor_output
    # Regression guard: the stale "not installed" WARN must NOT appear in normal state.
    assert "Agent-only exclude patterns not installed" not in doctor_output


def test_doctor_agent_count_matches_repo(doctor_output: str) -> None:
    m = re.search(r"\[OK\]\s+Found (\d+) agent\(s\)", doctor_output)
    assert m is not None, doctor_output
    on_disk = len(list((REPO_ROOT / ".opencode" / "agents").glob("*.md")))
    assert int(m.group(1)) == on_disk


def test_doctor_skill_count_matches_repo(doctor_output: str) -> None:
    m = re.search(r"\[OK\]\s+Found (\d+) skill\(s\)", doctor_output)
    assert m is not None, doctor_output
    on_disk = sum(
        1
        for d in (REPO_ROOT / ".opencode" / "skills").iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    )
    assert int(m.group(1)) == on_disk


def test_doctor_command_count_matches_repo(doctor_output: str) -> None:
    m = re.search(r"\[OK\]\s+Found (\d+) command\(s\)", doctor_output)
    assert m is not None, doctor_output
    on_disk = len(list((REPO_ROOT / ".opencode" / "commands").glob("*.md")))
    assert int(m.group(1)) == on_disk


def test_doctor_mcp_lists_all_declared_servers(doctor_output: str) -> None:
    """Every MCP server declared in opencode.json appears in the doctor output."""
    cfg = json.loads((REPO_ROOT / "opencode.json").read_text(encoding="utf-8-sig"))
    declared = sorted(cfg.get("mcp", {}).keys())
    for server in declared:
        # name appears in `[OK] <name>: ...` line
        assert re.search(rf"\[OK\]\s+{re.escape(server)}:", doctor_output), (
            f"MCP server {server!r} missing from doctor output"
        )
