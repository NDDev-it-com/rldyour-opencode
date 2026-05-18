"""Tests for `references/mcp-profiles.json` and `scripts/validate_mcp_profiles.py`.

Closes audit P1-3: MCP profile mappings move from prose in
`docs/security/mcp-trust-boundaries.md` to a machine-readable contract.
These tests pin both the file shape and the live-repo invariants the
validator enforces.

Every `subprocess.run` here arms an explicit `timeout=` per audit P0-4.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILES_PATH = REPO_ROOT / "references" / "mcp-profiles.json"
OPENCODE_JSON = REPO_ROOT / "opencode.json"
SKILLS_INDEX = REPO_ROOT / ".opencode" / "skills" / "index.json"
VALIDATOR = REPO_ROOT / "scripts" / "validate_mcp_profiles.py"

DEFAULT_TIMEOUT = 30


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Structural assertions on the live file
# ---------------------------------------------------------------------------


def test_profiles_file_exists() -> None:
    assert PROFILES_PATH.exists(), "references/mcp-profiles.json must exist (P1-3)"


def test_profiles_file_has_required_shape() -> None:
    data = _load_json(PROFILES_PATH)
    assert "version" in data
    assert "profiles" in data and isinstance(data["profiles"], dict)
    for name, body in data["profiles"].items():
        assert "description" in body, f"profile {name!r} missing description"
        assert "members" in body and isinstance(body["members"], list), (
            f"profile {name!r} missing members list"
        )


def test_every_opencode_mcp_server_is_assigned_to_a_profile() -> None:
    profiles = _load_json(PROFILES_PATH)
    cfg = _load_json(OPENCODE_JSON)
    declared = set((cfg.get("mcp") or {}).keys())
    assigned: set[str] = set()
    for body in profiles["profiles"].values():
        assigned.update(body["members"])
    missing = declared - assigned
    assert not missing, (
        f"servers declared in opencode.json.mcp but not assigned to any profile: "
        f"{sorted(missing)}"
    )


def test_no_server_appears_in_multiple_profiles() -> None:
    profiles = _load_json(PROFILES_PATH)
    seen: dict[str, str] = {}
    for name, body in profiles["profiles"].items():
        for server in body["members"]:
            if server in seen:
                raise AssertionError(
                    f"server {server!r} listed in both {seen[server]!r} and {name!r}"
                )
            seen[server] = name


def test_profiles_only_reference_declared_servers() -> None:
    profiles = _load_json(PROFILES_PATH)
    cfg = _load_json(OPENCODE_JSON)
    declared = set((cfg.get("mcp") or {}).keys())
    for name, body in profiles["profiles"].items():
        for server in body["members"]:
            assert server in declared, (
                f"profile {name!r} references {server!r} which is not in opencode.json.mcp"
            )


def test_high_context_members_exist_in_mcp() -> None:
    profiles = _load_json(PROFILES_PATH)
    cfg = _load_json(OPENCODE_JSON)
    declared = set((cfg.get("mcp") or {}).keys())
    high = set((profiles.get("high_context") or {}).get("members") or [])
    for server in high:
        assert server in declared, (
            f"high_context server {server!r} not declared in opencode.json.mcp"
        )


# ---------------------------------------------------------------------------
# Validator behaviour
# ---------------------------------------------------------------------------


def _run(*extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *extra_args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_TIMEOUT,
    )


def test_validator_passes_on_live_repo() -> None:
    proc = _run()
    assert proc.returncode == 0, (
        f"validator failed at HEAD\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "[OK]" in proc.stdout


def test_validator_json_envelope() -> None:
    proc = _run("--json")
    assert proc.returncode == 0, proc.stderr[:500]
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["problems"] == []
    assert isinstance(payload["warnings"], list)


def test_validator_detects_unassigned_server(tmp_path: Path) -> None:
    """An opencode.json server that is missing from every profile must fail."""
    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {"serena": {"type": "local"}, "ghost": {"type": "remote", "url": "https://x"}},
    }
    profiles = {
        "version": 1,
        "profiles": {"base": {"description": "x", "members": ["serena"]}},
    }
    (tmp_path / "opencode.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "profiles.json").write_text(json.dumps(profiles), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--profiles",
            str(tmp_path / "profiles.json"),
            "--opencode",
            str(tmp_path / "opencode.json"),
            "--skills-index",
            str(tmp_path / "missing-index.json"),
            "--json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_TIMEOUT,
    )
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert any("ghost" in p for p in payload["problems"]), payload["problems"]


def test_validator_detects_duplicate_membership(tmp_path: Path) -> None:
    cfg = {"mcp": {"serena": {"type": "local"}}}
    profiles = {
        "version": 1,
        "profiles": {
            "base": {"description": "x", "members": ["serena"]},
            "research": {"description": "y", "members": ["serena"]},
        },
    }
    (tmp_path / "opencode.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "profiles.json").write_text(json.dumps(profiles), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--profiles",
            str(tmp_path / "profiles.json"),
            "--opencode",
            str(tmp_path / "opencode.json"),
            "--skills-index",
            str(tmp_path / "missing-index.json"),
            "--json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_TIMEOUT,
    )
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert any("multiple profiles" in p for p in payload["problems"]), payload["problems"]


def test_validator_skill_requires_unknown_mcp(tmp_path: Path) -> None:
    """A skill requiring an MCP server not in opencode.json must fail."""
    cfg = {"mcp": {"serena": {"type": "local"}}}
    profiles = {
        "version": 1,
        "profiles": {"base": {"description": "x", "members": ["serena"]}},
    }
    skills_index = {
        "version": 1,
        "skills": [
            {"name": "bogus-skill", "domain": "flow", "requires_mcp": ["ghost"], "network": False}
        ],
    }
    (tmp_path / "opencode.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "profiles.json").write_text(json.dumps(profiles), encoding="utf-8")
    (tmp_path / "skills-index.json").write_text(json.dumps(skills_index), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--profiles",
            str(tmp_path / "profiles.json"),
            "--opencode",
            str(tmp_path / "opencode.json"),
            "--skills-index",
            str(tmp_path / "skills-index.json"),
            "--json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_TIMEOUT,
    )
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert any("ghost" in p for p in payload["problems"])


def test_validator_high_context_soft_warning(tmp_path: Path) -> None:
    """A skill that depends on a high_context server emits a soft warning."""
    cfg = {"mcp": {"github": {"type": "remote", "url": "https://x"}}}
    profiles = {
        "version": 1,
        "profiles": {"repo": {"description": "x", "members": ["github"]}},
        "high_context": {"description": "heavy", "members": ["github"]},
    }
    skills_index = {
        "version": 1,
        "skills": [
            {"name": "uses-github", "domain": "flow", "requires_mcp": ["github"], "network": True}
        ],
    }
    (tmp_path / "opencode.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "profiles.json").write_text(json.dumps(profiles), encoding="utf-8")
    (tmp_path / "skills-index.json").write_text(json.dumps(skills_index), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--profiles",
            str(tmp_path / "profiles.json"),
            "--opencode",
            str(tmp_path / "opencode.json"),
            "--skills-index",
            str(tmp_path / "skills-index.json"),
            "--json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_TIMEOUT,
    )
    assert proc.returncode == 0, proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["warnings"], payload
    assert any("high-context" in w for w in payload["warnings"])


def test_validator_missing_profiles_file_returns_two(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--profiles",
            str(tmp_path / "no.json"),
            "--opencode",
            str(OPENCODE_JSON),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_TIMEOUT,
    )
    assert proc.returncode == 2
    assert "required file missing" in proc.stderr


# Use shutil so the import is not flagged unused on platforms where the
# fixture-based tests do not exercise it.
_ = shutil
