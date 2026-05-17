"""Integration tests for scripts/fullrepo_sync.sh."""
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
    subprocess.run(["git", "init", "--initial-branch=main"], check=True, capture_output=True, cwd=tmp_path)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], check=True, cwd=tmp_path)
    subprocess.run(["git", "config", "user.name", "Fullrepo Test"], check=True, cwd=tmp_path)
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
        ("local_fullrepo_matches_worktree", bool),
        ("remote_fullrepo_matches_worktree", bool),
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
    exclude_file = tmp_path / ".git" / "info" / "exclude"
    exclude_file.write_text(
        "# rldyour-opencode agent-only\n"
        "AGENTS.md\n"
        ".opencode/\n"
        ".serena/\n"
        ".claude/\n"
        "docs/\n"
        "references/\n"
        "scripts/\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["bash", str(tmp_script), "install-exclude"],
        check=True,
        capture_output=True,
        cwd=tmp_path,
    )
    exclude_text = exclude_file.read_text(encoding="utf-8")
    assert "# >>> rldyour fullrepo agent-only files >>>" in exclude_text
    assert "# <<< rldyour fullrepo agent-only files <<<" in exclude_text
    assert "# rldyour-opencode agent-only" not in exclude_text
    assert "\n.opencode/\n" not in exclude_text
    assert "\ndocs/\n" not in exclude_text
    assert "\nreferences/\n" not in exclude_text
    assert "\nscripts/\n" not in exclude_text


def test_publish_creates_complete_head_plus_agent_snapshot(tmp_path: Path) -> None:
    """`fullrepo` must be a complete portable snapshot, not an agent-only
    tree that omits root manifests such as opencode.json / VERSION."""
    tmp_script = _copy_script_to_tmp_repo(tmp_path)
    (tmp_path / "opencode.json").write_text('{"model":"opencode/test"}\n', encoding="utf-8")
    (tmp_path / "VERSION").write_text("0.0.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "validate.yml").write_text("name: validate\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "tracked.md").write_text("# Tracked docs\n", encoding="utf-8")
    (tmp_path / "references").mkdir()
    (tmp_path / "references" / "tracked.md").write_text("# Tracked refs\n", encoding="utf-8")
    subprocess.run(["git", "add", "opencode.json", "VERSION", "README.md", ".github", "docs", "references", "scripts"], check=True, cwd=tmp_path)
    subprocess.run(["git", "commit", "-m", "test: seed main"], check=True, capture_output=True, cwd=tmp_path)

    origin = tmp_path.parent / f"{tmp_path.name}-origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True, cwd=tmp_path)
    subprocess.run(["git", "remote", "add", "origin", str(origin)], check=True, cwd=tmp_path)
    subprocess.run(["git", "push", "-u", "origin", "main"], check=True, capture_output=True, cwd=tmp_path)

    (tmp_path / "AGENTS.md").write_text("# Agent Instructions\n", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "CLAUDE.md").write_text("# Claude Instructions\n", encoding="utf-8")
    (tmp_path / ".serena" / "memories").mkdir(parents=True)
    (tmp_path / ".serena" / "memories" / "CORE-01-INDEX.md").write_text("Last commit: fixture\n", encoding="utf-8")
    (tmp_path / ".serena" / ".flow_sync_marker").write_text("runtime-marker\n", encoding="utf-8")
    (tmp_path / "docs" / "local-only.md").write_text("must not publish from working tree\n", encoding="utf-8")
    (tmp_path / "references" / "local-only.md").write_text("must not publish from working tree\n", encoding="utf-8")
    (tmp_path / "scripts" / "local-only.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    with (tmp_path / ".git" / "info" / "exclude").open("a", encoding="utf-8") as exclude:
        exclude.write("\ndocs/local-only.md\nreferences/local-only.md\nscripts/local-only.sh\n")

    subprocess.run(["bash", str(tmp_script), "publish"], check=True, capture_output=True, cwd=tmp_path)

    tree = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "origin/fullrepo"],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    ).stdout.splitlines()
    assert "opencode.json" in tree
    assert "VERSION" in tree
    assert ".github/workflows/validate.yml" in tree
    assert "docs/tracked.md" in tree
    assert "references/tracked.md" in tree
    assert "AGENTS.md" in tree
    assert ".claude/CLAUDE.md" in tree
    assert ".serena/memories/CORE-01-INDEX.md" in tree
    assert ".serena/.flow_sync_marker" not in tree
    assert "docs/local-only.md" not in tree
    assert "references/local-only.md" not in tree
    assert "scripts/local-only.sh" not in tree

    status = subprocess.run(
        ["bash", str(tmp_script), "status-json"],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    parsed = json.loads(status.stdout)
    assert parsed["local_fullrepo_matches_worktree"] is True
    assert parsed["remote_fullrepo_matches_worktree"] is True


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
