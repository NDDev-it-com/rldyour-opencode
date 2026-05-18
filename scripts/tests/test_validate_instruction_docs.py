"""Self-tests for `scripts/validate_instruction_docs.py`.

Exercises the four documented check_doc paths:
  - missing file → fail
  - file too short → fail
  - missing required heading → fail
  - all-good → ok

Plus JSON envelope and CLI exit codes. tmp_path fixtures keep the
project's real AGENTS.md and CLAUDE.md untouched.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODULE_PATH = PROJECT_ROOT / "scripts" / "validate_instruction_docs.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("validate_instruction_docs", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_instruction_docs"] = module
    spec.loader.exec_module(module)
    return module


validator = _load_module()


# ---------------------------------------------------------------------------
# check_doc paths
# ---------------------------------------------------------------------------

def _spec(tmp_path: Path, name: str, min_bytes: int, headings: tuple[str, ...]) -> dict[str, Any]:
    return {
        "path": tmp_path / name,
        "min_bytes": min_bytes,
        "required_headings": headings,
    }


def test_missing_file_fails(tmp_path: Path) -> None:
    spec = _spec(tmp_path, "missing.md", 100, ("## Heading",))
    result = validator.check_doc(spec)
    assert result["status"] == "fail"
    assert result["reason"] == "missing"


def test_too_short_file_fails(tmp_path: Path) -> None:
    target = tmp_path / "short.md"
    target.write_text("# tiny\n", encoding="utf-8")
    spec = _spec(tmp_path, "short.md", 1024, ("# tiny",))
    result = validator.check_doc(spec)
    assert result["status"] == "fail"
    assert "1024" in result["reason"]


def test_missing_heading_fails(tmp_path: Path) -> None:
    target = tmp_path / "doc.md"
    target.write_text("padding\n" * 200 + "## Wrong Heading\n", encoding="utf-8")
    spec = _spec(tmp_path, "doc.md", 100, ("## Required",))
    result = validator.check_doc(spec)
    assert result["status"] == "fail"
    assert "missing required headings" in result["reason"]
    assert result["missing_headings"] == ["## Required"]


def test_all_good_passes(tmp_path: Path) -> None:
    target = tmp_path / "doc.md"
    target.write_text(
        "intro line\n" * 100 + "\n## First Heading\n\nbody\n\n## Second Heading\n\nmore body\n",
        encoding="utf-8",
    )
    spec = _spec(tmp_path, "doc.md", 100, ("## First Heading", "## Second Heading"))
    result = validator.check_doc(spec)
    assert result["status"] == "ok"
    assert result["headings"] == 2
    assert result["bytes"] > 100


# ---------------------------------------------------------------------------
# main(): exit codes + JSON envelope
# ---------------------------------------------------------------------------

def test_main_exit_zero_when_all_pass(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Patch DOCS to a single all-good spec and run main(); exit 0."""
    target = tmp_path / "good.md"
    target.write_text(
        "x" * 5000 + "\n## Required Heading\n",
        encoding="utf-8",
    )
    fake_docs = [
        {
            "path": target,
            "min_bytes": 100,
            "required_headings": ("## Required Heading",),
        }
    ]
    with mock.patch.object(validator, "DOCS", fake_docs):
        with mock.patch.object(sys, "argv", ["validate_instruction_docs.py"]):
            rc = validator.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "[OK]" in out
    assert "0 failed" in out


def test_main_exit_one_when_any_fail(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Patch DOCS to include a missing file → exit 1."""
    fake_docs = [
        {
            "path": tmp_path / "missing.md",
            "min_bytes": 100,
            "required_headings": ("## X",),
        }
    ]
    with mock.patch.object(validator, "DOCS", fake_docs):
        with mock.patch.object(sys, "argv", ["validate_instruction_docs.py"]):
            rc = validator.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "[FAIL]" in out


def test_main_json_mode_emits_envelope(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """--json mode emits a valid envelope with results / failed / total."""
    fake_docs = [
        {
            "path": tmp_path / "missing.md",
            "min_bytes": 100,
            "required_headings": ("## X",),
        }
    ]
    with mock.patch.object(validator, "DOCS", fake_docs):
        with mock.patch.object(sys, "argv", ["validate_instruction_docs.py", "--json"]):
            rc = validator.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 1
    assert set(payload.keys()) >= {"results", "failed", "skipped", "total"}
    assert payload["failed"] == 1
    assert payload["total"] == 1


def test_agent_docs_are_skipped_without_strict_flag(tmp_path: Path) -> None:
    """Missing docs with ``agent=True`` become [SKIP] only in non-strict mode."""
    agent_docs = {
        "path": tmp_path / "AGENTS.md",
        "min_bytes": 100,
        "agent": True,
        "required_headings": ("## Required",),
    }
    fake_docs = [{"path": agent_docs["path"], "min_bytes": 100, "agent": True, "required_headings": ("## Required",)}]
    with mock.patch.object(validator, "DOCS", fake_docs):
        result = validator.check_doc(agent_docs)
    assert result["status"] == "skip"
    assert result["reason"] == "missing (agent doc)"


def test_require_agent_docs_flag_enforces_agent_paths(tmp_path: Path) -> None:
    """--require-agent-docs turns agent doc skips into hard failures."""
    missing_agent_doc = {
        "path": tmp_path / "AGENTS.md",
        "min_bytes": 100,
        "agent": True,
        "required_headings": ("## Required",),
    }
    with mock.patch.object(sys, "argv", ["validate_instruction_docs.py", "--require-agent-docs"]):
        with mock.patch.object(validator, "DOCS", [missing_agent_doc]):
            rc = validator.main()
    assert rc == 1


def test_main_json_mode_marks_skipped_count(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """JSON envelope must reflect non-fatal agent-doc skips separately from failures."""
    fake_docs = [
        {
            "path": tmp_path / "AGENTS.md",
            "min_bytes": 100,
            "agent": True,
            "required_headings": ("## Required",),
        },
        {
            "path": tmp_path / "missing.md",
            "min_bytes": 100,
            "required_headings": ("## Required",),
        },
    ]
    with mock.patch.object(sys, "argv", ["validate_instruction_docs.py", "--json"]):
        with mock.patch.object(validator, "DOCS", fake_docs):
            rc = validator.main()
    out = capsys.readouterr().out
    assert rc == 1
    payload = json.loads(out or "")
    assert payload["failed"] == 1
    assert payload["skipped"] == 1
