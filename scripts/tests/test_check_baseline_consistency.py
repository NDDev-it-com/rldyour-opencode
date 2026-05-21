"""Tests for `scripts/check_baseline_consistency.py`.

The baseline validator was introduced to close audit P0-1: docs were
declaring `@opencode-ai/plugin@1.15.4` while `.opencode/package.json`
and `bun.lock` still pinned `1.15.3`. The validator reads
`references/opencode-baseline.json` and asserts every place the repo
names an OpenCode/runtime pin agrees with it.

These tests run the live validator against the live repository — the
expected outcome at HEAD is a clean exit, but the suite also exercises
every drift-detection path via temporary baseline files and a copy of
the script that points at fixture inputs. Every subprocess call here
arms an explicit `timeout=` per audit P0-4.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_baseline_consistency.py"
BASELINE_FILE = REPO_ROOT / "references" / "opencode-baseline.json"

DEFAULT_TIMEOUT = 30


def _run_live(*extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *extra_args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_TIMEOUT,
    )


# ---------------------------------------------------------------------------
# Live repository assertions
# ---------------------------------------------------------------------------


def test_baseline_file_exists() -> None:
    assert BASELINE_FILE.exists(), (
        "references/opencode-baseline.json must exist; it is the single source "
        "of truth for every pinned version the marketplace targets"
    )


def test_baseline_file_has_required_keys() -> None:
    data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    assert data.get("baseline"), "baseline.baseline must be present and non-empty"
    bl = data["baseline"]
    for required in (
        "opencode_cli",
        "plugin_sdk",
        "sdk",
        "config_schema",
        "bun_runtime",
        "python_runtime",
        "test_dependencies",
        "security_tooling",
    ):
        assert required in bl, f"baseline.{required} missing"
    assert "version" in bl["plugin_sdk"]
    assert "version" in bl["sdk"]
    assert "version" in bl["opencode_cli"]
    assert "version" in bl["bun_runtime"]


def test_script_runs_clean_on_live_repo() -> None:
    """At HEAD the baseline must be consistent (hard problems == 0)."""
    proc = _run_live()
    assert proc.returncode == 0, (
        f"baseline drift at HEAD:\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )
    assert "[OK]" in proc.stdout


def test_script_json_mode_emits_valid_envelope() -> None:
    proc = _run_live("--json")
    assert proc.returncode == 0, proc.stderr[:500]
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["problems"] == []
    assert isinstance(payload["warnings"], list)
    assert "baseline" in payload
    assert payload["baseline"]["plugin_sdk"]["version"] == json.loads(
        BASELINE_FILE.read_text(encoding="utf-8")
    )["baseline"]["plugin_sdk"]["version"]


def test_script_no_changelog_skips_soft_check() -> None:
    """`--no-changelog` must suppress the soft CHANGELOG mention warning."""
    proc = _run_live("--no-changelog", "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["warnings"] == [], (
        "--no-changelog must suppress the soft CHANGELOG warning entirely"
    )


def test_live_changelog_documents_current_baseline() -> None:
    """The current baseline may be documented in Unreleased before it ships."""
    proc = _run_live("--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["warnings"] == []


# ---------------------------------------------------------------------------
# Drift detection via fixture baseline
# ---------------------------------------------------------------------------


def _copy_script_with_fixture_baseline(
    tmp_path: Path, baseline_override: dict[str, Any]
) -> Path:
    """Materialise the script + a fixture baseline into a temp repo skeleton
    that mirrors REPO_ROOT layout. Returns the script path under tmp_path."""
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "references").mkdir(parents=True)
    (tmp_path / ".opencode").mkdir(parents=True)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    shutil.copy2(SCRIPT, tmp_path / "scripts" / "check_baseline_consistency.py")
    (tmp_path / "references" / "opencode-baseline.json").write_text(
        json.dumps({"baseline": baseline_override}, indent=2), encoding="utf-8"
    )
    (tmp_path / "LICENSE").write_text(
        "Copyright (C) 2026 Danil Silantyev (github:rldyourmnd), CEO NDDev\n"
        "This project is licensed under the GNU Affero General Public License, "
        "version 3 or later, as published by the Free Software Foundation.\n"
        "\n"
        "GNU AFFERO GENERAL PUBLIC LICENSE\n",
        encoding="utf-8",
    )
    return tmp_path / "scripts" / "check_baseline_consistency.py"


def _seed_files(tmp_path: Path, files: dict[str, str]) -> None:
    for rel, contents in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel == ".opencode/package.json":
            data = json.loads(contents)
            data.setdefault("license", "AGPL-3.0-or-later")
            data.setdefault(
                "author",
                {
                    "name": "Danil Silantyev (github:rldyourmnd), CEO NDDev",
                    "email": "rldyourmnd@users.noreply.github.com",
                    "url": "https://github.com/rldyourmnd",
                },
            )
            contents = json.dumps(data)
        path.write_text(contents, encoding="utf-8")


_BASELINE_OK = {
    "opencode_cli": {"version": "1.15.4", "npm_package": "opencode-ai"},
    "plugin_sdk": {"version": "1.15.4", "npm_package": "@opencode-ai/plugin"},
    "sdk": {"version": "1.15.4", "npm_package": "@opencode-ai/sdk"},
    "config_schema": {
        "version": "v1.15.4",
        "vendored_at": "references/opencode-config.schema.v1.15.4.json",
        "external_refs_vendored_at": [],
    },
    "bun_runtime": {"version": "1.3.14"},
    "python_runtime": {"version": "3.13"},
    "test_dependencies": {
        "pytest": "9.0.3",
        "pyyaml": "6.0.3",
        "jsonschema": "4.26.0",
        "ruff": "0.15.13",
    },
    "security_tooling": {"gitleaks": "8.30.1", "codeql_action": "v4.35.5"},
}


def _run_fixture(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(tmp_path / "scripts" / "check_baseline_consistency.py"), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_TIMEOUT,
    )


def test_drift_detected_when_package_json_pins_older(tmp_path: Path) -> None:
    _copy_script_with_fixture_baseline(tmp_path, _BASELINE_OK)
    _seed_files(
        tmp_path,
        {
            ".opencode/package.json": json.dumps(
                {"dependencies": {"@opencode-ai/plugin": "1.15.3"}}
            ),
            ".opencode/bun.lock": (
                '"@opencode-ai/plugin": ["@opencode-ai/plugin@1.15.4"\n'
                '"@opencode-ai/sdk": ["@opencode-ai/sdk@1.15.4"\n'
            ),
            "references/opencode-config.schema.v1.15.4.json": "{}",
            "CHANGELOG.md": "## [0.12.2]\n@opencode-ai/plugin@1.15.4\n",
            ".github/workflows/opencode-runtime.yml": (
                'install -g opencode-ai@1.15.4\nbun-version: "1.3.14"\n'
            ),
        },
    )
    proc = _run_fixture(tmp_path, "--json")
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert any(
        ".opencode/package.json" in p and "1.15.3" in p for p in payload["problems"]
    ), payload["problems"]


def test_drift_detected_when_license_grant_is_not_or_later(tmp_path: Path) -> None:
    _copy_script_with_fixture_baseline(tmp_path, _BASELINE_OK)
    (tmp_path / "LICENSE").write_text(
        "Copyright (C) 2026 Danil Silantyev (github:rldyourmnd), CEO NDDev\n"
        "This project is licensed under the GNU Affero General Public License, "
        "version 3, as published by the Free Software Foundation.\n"
        "\n"
        "GNU AFFERO GENERAL PUBLIC LICENSE\n",
        encoding="utf-8",
    )
    _seed_files(
        tmp_path,
        {
            ".opencode/package.json": json.dumps(
                {"dependencies": {"@opencode-ai/plugin": "1.15.4"}}
            ),
            ".opencode/bun.lock": (
                '"@opencode-ai/plugin": ["@opencode-ai/plugin@1.15.4"\n'
                '"@opencode-ai/sdk": ["@opencode-ai/sdk@1.15.4"\n'
            ),
            "references/opencode-config.schema.v1.15.4.json": "{}",
            "CHANGELOG.md": "## [0.12.2]\n@opencode-ai/plugin@1.15.4\n",
            ".github/workflows/opencode-runtime.yml": (
                'install -g opencode-ai@1.15.4\nbun-version: "1.3.14"\n'
            ),
        },
    )
    proc = _run_fixture(tmp_path, "--json")
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert any("LICENSE grant must be AGPL-3.0-or-later" in p for p in payload["problems"])


def test_drift_detected_when_bun_lock_pins_older(tmp_path: Path) -> None:
    _copy_script_with_fixture_baseline(tmp_path, _BASELINE_OK)
    _seed_files(
        tmp_path,
        {
            ".opencode/package.json": json.dumps(
                {"dependencies": {"@opencode-ai/plugin": "1.15.4"}}
            ),
            ".opencode/bun.lock": (
                '"@opencode-ai/plugin": ["@opencode-ai/plugin@1.15.3"\n'
                '"@opencode-ai/sdk": ["@opencode-ai/sdk@1.15.3"\n'
            ),
            "references/opencode-config.schema.v1.15.4.json": "{}",
            "CHANGELOG.md": "## [0.12.2]\n@opencode-ai/plugin@1.15.4\n",
            ".github/workflows/opencode-runtime.yml": (
                'install -g opencode-ai@1.15.4\nbun-version: "1.3.14"\n'
            ),
        },
    )
    proc = _run_fixture(tmp_path, "--json")
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert any("plugin resolved to '1.15.3'" in p for p in payload["problems"]), (
        payload["problems"]
    )


def test_drift_detected_when_runtime_workflow_pin_disagrees(tmp_path: Path) -> None:
    _copy_script_with_fixture_baseline(tmp_path, _BASELINE_OK)
    _seed_files(
        tmp_path,
        {
            ".opencode/package.json": json.dumps(
                {"dependencies": {"@opencode-ai/plugin": "1.15.4"}}
            ),
            ".opencode/bun.lock": (
                '"@opencode-ai/plugin": ["@opencode-ai/plugin@1.15.4"\n'
                '"@opencode-ai/sdk": ["@opencode-ai/sdk@1.15.4"\n'
            ),
            "references/opencode-config.schema.v1.15.4.json": "{}",
            "CHANGELOG.md": "## [0.12.2]\n@opencode-ai/plugin@1.15.4\n",
            ".github/workflows/opencode-runtime.yml": (
                'install -g opencode-ai@1.14.0\nbun-version: "1.3.14"\n'
            ),
        },
    )
    proc = _run_fixture(tmp_path, "--json")
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert any("opencode-ai@" in p and "1.14.0" in p for p in payload["problems"]), (
        payload["problems"]
    )


def test_drift_detected_when_bun_version_disagrees(tmp_path: Path) -> None:
    _copy_script_with_fixture_baseline(tmp_path, _BASELINE_OK)
    _seed_files(
        tmp_path,
        {
            ".opencode/package.json": json.dumps(
                {"dependencies": {"@opencode-ai/plugin": "1.15.4"}}
            ),
            ".opencode/bun.lock": (
                '"@opencode-ai/plugin": ["@opencode-ai/plugin@1.15.4"\n'
                '"@opencode-ai/sdk": ["@opencode-ai/sdk@1.15.4"\n'
            ),
            "references/opencode-config.schema.v1.15.4.json": "{}",
            "CHANGELOG.md": "## [0.12.2]\n@opencode-ai/plugin@1.15.4\n",
            ".github/workflows/opencode-runtime.yml": (
                'install -g opencode-ai@1.15.4\nbun-version: "1.0.0"\n'
            ),
        },
    )
    proc = _run_fixture(tmp_path, "--json")
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert any("bun-version" in p and "1.0.0" in p for p in payload["problems"]), (
        payload["problems"]
    )


def test_drift_detected_when_pip_install_pin_disagrees(tmp_path: Path) -> None:
    _copy_script_with_fixture_baseline(tmp_path, _BASELINE_OK)
    _seed_files(
        tmp_path,
        {
            ".opencode/package.json": json.dumps(
                {"dependencies": {"@opencode-ai/plugin": "1.15.4"}}
            ),
            ".opencode/bun.lock": (
                '"@opencode-ai/plugin": ["@opencode-ai/plugin@1.15.4"\n'
                '"@opencode-ai/sdk": ["@opencode-ai/sdk@1.15.4"\n'
            ),
            "references/opencode-config.schema.v1.15.4.json": "{}",
            "CHANGELOG.md": "## [0.12.2]\n@opencode-ai/plugin@1.15.4\n",
            ".github/workflows/opencode-runtime.yml": (
                'install -g opencode-ai@1.15.4\nbun-version: "1.3.14"\n'
            ),
            ".github/workflows/validate.yml": (
                'pip install --upgrade pip "pytest==9.0.0" "PyYAML==6.0.3"\n'
            ),
        },
    )
    proc = _run_fixture(tmp_path, "--json")
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert any("pytest" in p and "9.0.0" in p for p in payload["problems"]), (
        payload["problems"]
    )


def test_drift_detected_when_vendored_schema_missing(tmp_path: Path) -> None:
    _copy_script_with_fixture_baseline(tmp_path, _BASELINE_OK)
    _seed_files(
        tmp_path,
        {
            ".opencode/package.json": json.dumps(
                {"dependencies": {"@opencode-ai/plugin": "1.15.4"}}
            ),
            ".opencode/bun.lock": (
                '"@opencode-ai/plugin": ["@opencode-ai/plugin@1.15.4"\n'
                '"@opencode-ai/sdk": ["@opencode-ai/sdk@1.15.4"\n'
            ),
            "CHANGELOG.md": "## [0.12.2]\n@opencode-ai/plugin@1.15.4\n",
            ".github/workflows/opencode-runtime.yml": (
                'install -g opencode-ai@1.15.4\nbun-version: "1.3.14"\n'
            ),
            # NOTE: references/opencode-config.schema.v1.15.4.json intentionally omitted
        },
    )
    proc = _run_fixture(tmp_path, "--json")
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert any("vendored schema missing" in p for p in payload["problems"]), (
        payload["problems"]
    )


def test_soft_warning_surfaces_when_changelog_omits_plugin_version(tmp_path: Path) -> None:
    _copy_script_with_fixture_baseline(tmp_path, _BASELINE_OK)
    _seed_files(
        tmp_path,
        {
            ".opencode/package.json": json.dumps(
                {"dependencies": {"@opencode-ai/plugin": "1.15.4"}}
            ),
            ".opencode/bun.lock": (
                '"@opencode-ai/plugin": ["@opencode-ai/plugin@1.15.4"\n'
                '"@opencode-ai/sdk": ["@opencode-ai/sdk@1.15.4"\n'
            ),
            "references/opencode-config.schema.v1.15.4.json": "{}",
            # CHANGELOG omits the plugin version on purpose to trigger the soft check
            "CHANGELOG.md": "## [0.0.1]\nUnrelated note\n",
            ".github/workflows/opencode-runtime.yml": (
                'install -g opencode-ai@1.15.4\nbun-version: "1.3.14"\n'
            ),
        },
    )
    proc = _run_fixture(tmp_path, "--json")
    assert proc.returncode == 0, proc.stdout  # soft warnings don't fail
    payload = json.loads(proc.stdout)
    assert payload["warnings"], "expected a soft CHANGELOG warning"
    assert any("1.15.4" in w for w in payload["warnings"])


def test_changelog_soft_check_skips_unreleased_block(tmp_path: Path) -> None:
    _copy_script_with_fixture_baseline(tmp_path, _BASELINE_OK)
    _seed_files(
        tmp_path,
        {
            ".opencode/package.json": json.dumps(
                {"dependencies": {"@opencode-ai/plugin": "1.15.4"}}
            ),
            ".opencode/bun.lock": (
                '"@opencode-ai/plugin": ["@opencode-ai/plugin@1.15.4"\n'
                '"@opencode-ai/sdk": ["@opencode-ai/sdk@1.15.4"\n'
            ),
            "references/opencode-config.schema.v1.15.4.json": "{}",
            "CHANGELOG.md": (
                "## [Unreleased]\n\n"
                "## [0.13.0] - 2026-05-18\n"
                "@opencode-ai/plugin@1.15.4\n"
            ),
            ".github/workflows/opencode-runtime.yml": (
                'install -g opencode-ai@1.15.4\nbun-version: "1.3.14"\n'
            ),
        },
    )
    proc = _run_fixture(tmp_path, "--json")
    assert proc.returncode == 0, proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["warnings"] == []


def test_missing_baseline_returns_operational_error(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "references").mkdir()
    shutil.copy2(SCRIPT, tmp_path / "scripts" / "check_baseline_consistency.py")
    # No baseline file written
    proc = _run_fixture(tmp_path)
    assert proc.returncode == 2, proc.stderr[:500]
    assert "baseline missing" in proc.stderr


def test_invalid_baseline_json_returns_operational_error(tmp_path: Path) -> None:
    """Verification-review F-5: malformed JSON in opencode-baseline.json is
    an operational error, not a check failure, and must exit 2 with a
    clean message instead of crashing on JSONDecodeError."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "references").mkdir()
    shutil.copy2(SCRIPT, tmp_path / "scripts" / "check_baseline_consistency.py")
    (tmp_path / "references" / "opencode-baseline.json").write_text(
        "{ this is not valid json", encoding="utf-8"
    )
    proc = _run_fixture(tmp_path)
    assert proc.returncode == 2, proc.stderr[:500]
    assert "baseline parse" in proc.stderr


def test_drift_detected_when_referencing_pin_disagrees(tmp_path: Path) -> None:
    """Quality-review F-1 closure verification: a second/third pip-install
    package on the same line must be inspected. Use `referencing` as the
    trailing pin so the regex must walk past pytest/PyYAML/jsonschema to
    catch it."""
    _copy_script_with_fixture_baseline(tmp_path, _BASELINE_OK)
    _seed_files(
        tmp_path,
        {
            ".opencode/package.json": json.dumps(
                {"dependencies": {"@opencode-ai/plugin": "1.15.4"}}
            ),
            ".opencode/bun.lock": (
                '"@opencode-ai/plugin": ["@opencode-ai/plugin@1.15.4"\n'
                '"@opencode-ai/sdk": ["@opencode-ai/sdk@1.15.4"\n'
            ),
            "references/opencode-config.schema.v1.15.4.json": "{}",
            "CHANGELOG.md": "## [0.12.2]\n@opencode-ai/plugin@1.15.4\n",
            ".github/workflows/opencode-runtime.yml": (
                'install -g opencode-ai@1.15.4\nbun-version: "1.3.14"\n'
            ),
            # Trailing referencing pin drift (Quality-review F-1).
            ".github/workflows/validate.yml": (
                'pip install --upgrade pip "pytest==9.0.3" "PyYAML==6.0.3" '
                '"jsonschema==4.26.0" "referencing==0.30.0"\n'
            ),
        },
    )
    # The fixture baseline omits referencing, so add it explicitly to the
    # fixture file before running.
    fixture_baseline_path = tmp_path / "references" / "opencode-baseline.json"
    data = json.loads(fixture_baseline_path.read_text(encoding="utf-8"))
    data["baseline"]["test_dependencies"]["referencing"] = "0.36.2"
    fixture_baseline_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    proc = _run_fixture(tmp_path, "--json")
    assert proc.returncode == 1, proc.stdout
    payload = json.loads(proc.stdout)
    assert any(
        "referencing" in p and "0.30.0" in p for p in payload["problems"]
    ), payload["problems"]
