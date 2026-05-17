"""Integration tests for scripts/fullrepo_sync.sh.

The full publish path is not exercised here (it pushes to origin), but
status / status-json / bootstrap-init exclude-marker behaviour is. The
status-json shape is the only contract surface this suite asserts; the
publish path is exercised by manual smoke from /ry-sync.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = PROJECT_ROOT / "scripts" / "fullrepo_sync.sh"


# ---------- Script structural contract ----------


def test_script_has_strict_bash_header() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash"), "fullrepo_sync.sh must use env-bash shebang"
    assert "set -euo pipefail" in text, "fullrepo_sync.sh must enable strict mode"


def test_runtime_exclude_patterns_cover_command_audit_log() -> None:
    """Audit finding 4MUSTHAVE-13: the runtime audit log must be excluded
    from fullrepo publication; 0.10.x left this in only the gitignore."""
    text = SCRIPT.read_text(encoding="utf-8")
    # The exclude array uses one literal per line; assert verbatim membership.
    assert '".serena/.command_audit.log"' in text


def test_status_json_uses_python_escape() -> None:
    """Audit finding 4MUSTHAVE-PA-015: status-json output must go through
    a real JSON serializer (python json.dumps) instead of heredoc
    interpolation that breaks on quote characters in branch names."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "json.dumps" in text, "status-json must use json.dumps for safety"
    # Negative assertion — the legacy heredoc form must not coexist.
    assert "cat <<EOF\n{\n" not in text


def test_secret_scan_uses_recursive_text_grep() -> None:
    """Audit finding 4MUSTHAVE-PA-007: secret scan must cover all text
    files via `grep -rI`, not a fixed include-list that misses *.py /
    extension-less files."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "grep -rIE" in text
    # Defensive — the legacy include-list form must not coexist.
    assert "--include='*.md'" not in text


# ---------- status-json runtime ----------


def _run_status_json() -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), "status-json"],
        check=True,
        capture_output=True,
        cwd=str(PROJECT_ROOT),
    )


def _copy_script_to_tmp_repo(tmp_path: Path) -> Path:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    tmp_script = scripts_dir / "fullrepo_sync.sh"
    tmp_script.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    subprocess.run(["git", "init"], check=True, capture_output=True, cwd=tmp_path)
    return tmp_script


def test_status_json_emits_well_formed_json() -> None:
    """The wrapper must always produce parsable JSON regardless of
    the local branch/dirty state."""
    result = _run_status_json()
    parsed = json.loads(result.stdout.decode("utf-8"))
    assert isinstance(parsed, dict)


@pytest.mark.parametrize(
    "field,expected_type",
    [
        ("branch", str),
        ("dirty", str),
        ("ahead", int),
        ("behind", int),
        ("fullrepo_local", bool),
        ("fullrepo_remote", bool),
        ("serena_memory_count", int),
    ],
)
def test_status_json_field_types(field: str, expected_type: type) -> None:
    """Each documented field must be present with the documented type."""
    result = _run_status_json()
    parsed = json.loads(result.stdout.decode("utf-8"))
    assert field in parsed, f"status-json missing required field {field!r}"
    assert isinstance(parsed[field], expected_type), (
        f"status-json field {field!r} is {type(parsed[field]).__name__}, expected {expected_type.__name__}"
    )


def test_status_json_dirty_is_clean_or_dirty() -> None:
    result = _run_status_json()
    parsed = json.loads(result.stdout.decode("utf-8"))
    assert parsed["dirty"] in ("clean", "dirty")


def test_status_json_handles_missing_serena_memories(tmp_path: Path) -> None:
    """GitHub runner checkouts do not restore `.serena` by default.

    `status-json` is a status command, so missing memories must report
    `serena_memory_count: 0` instead of exiting under `set -euo pipefail`.
    """
    tmp_script = _copy_script_to_tmp_repo(tmp_path)
    result = subprocess.run(
        ["bash", str(tmp_script), "status-json"],
        check=True,
        capture_output=True,
        cwd=tmp_path,
    )
    parsed = json.loads(result.stdout.decode("utf-8"))
    assert parsed["serena_memory_count"] == 0


def test_install_exclude_writes_canonical_marker(tmp_path: Path) -> None:
    tmp_script = _copy_script_to_tmp_repo(tmp_path)
    subprocess.run(
        ["bash", str(tmp_script), "install-exclude"],
        check=True,
        capture_output=True,
        cwd=tmp_path,
    )
    exclude_text = (tmp_path / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert "# >>> rldyour fullrepo agent-only files >>>" in exclude_text
    assert "# <<< rldyour fullrepo agent-only files <<<" in exclude_text


# ---------- help / usage ----------


def test_help_flag_is_recognised() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "-h"],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0
    assert b"bootstrap-init" in result.stdout
    assert b"publish" in result.stdout


def test_unknown_command_returns_nonzero() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "no-such-cmd"],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode != 0
