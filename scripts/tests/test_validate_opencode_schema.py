"""Tests for `scripts/validate_opencode_schema.py`.

The validator pins the OpenCode JSON Schema offline under
`references/opencode-config.schema.v1.17.6.json`. These tests exercise
the happy path (the real `opencode.json` validates) and a couple of
representative violations so the contract can't silently drift.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "validate_opencode_schema.py"
DEFAULT_SCHEMA = REPO_ROOT / "references" / "opencode-config.schema.v1.17.6.json"
DEFAULT_CONFIG = REPO_ROOT / "opencode.json"

JSONSCHEMA_AVAILABLE = importlib.util.find_spec("jsonschema") is not None


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_schema_file_exists() -> None:
    assert DEFAULT_SCHEMA.exists(), (
        f"Vendored schema {DEFAULT_SCHEMA} is missing. Re-fetch from "
        f"https://opencode.ai/config.json or restore from history."
    )


def test_schema_targets_jsonschema_draft_2020_12() -> None:
    schema = json.loads(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"


def test_default_config_exists() -> None:
    assert DEFAULT_CONFIG.exists()


def test_default_config_references_pinned_schema_url() -> None:
    cfg = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    assert cfg.get("$schema") == "https://opencode.ai/config.json"


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
def test_real_opencode_json_validates_clean() -> None:
    result = _run([])
    assert result.returncode == 0, (
        f"opencode.json failed schema validation:\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "[OK]" in result.stdout


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
def test_missing_schema_returns_two(tmp_path: Path) -> None:
    nonexistent = tmp_path / "missing.json"
    result = _run(["--schema", str(nonexistent)])
    assert result.returncode == 2
    assert "schema not found" in result.stderr


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
def test_invalid_config_rejected(tmp_path: Path) -> None:
    bad_config = tmp_path / "opencode.json"
    bad_config.write_text(
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "model": 42,  # must be string
                "permission": {"unknownKey": "allow"},
            },
        ),
        encoding="utf-8",
    )
    result = _run(["--config", str(bad_config)])
    assert result.returncode == 1
    assert "schema violation" in result.stderr


@pytest.mark.skipif(JSONSCHEMA_AVAILABLE, reason="jsonschema is installed; cannot test the missing-import path")
def test_missing_jsonschema_returns_two() -> None:
    result = _run([])
    assert result.returncode == 2
    assert "library not available" in result.stderr
