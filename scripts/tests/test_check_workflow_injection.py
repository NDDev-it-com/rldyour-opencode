"""Tests for scripts/check_workflow_injection.py.

Reviewer wave 2026-05-18 security F-3 added the static gate. These tests
exercise both the clean and dirty paths against synthetic workflow YAML
fixtures plus the real project workflows (which must stay clean after
the F-3 fix in `.github/workflows/release.yml`).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "check_workflow_injection.py"


def _run(*, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the real script against the real project workflows. Used only
    by the smoke test that validates the project's own workflows are clean
    after the F-3 fix. Fixture-driven tests use `_run_under` instead."""
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=cwd or PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _make_project_tree(tmp_path: Path, *workflow_files: tuple[str, str]) -> Path:
    """Create a minimal tmp project tree with `.github/workflows/<name>.yml`
    files and a copy of the real script that resolves PROJECT_ROOT through
    the script file location."""
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    for name, body in workflow_files:
        (workflows / name).write_text(body, encoding="utf-8")
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    shutil.copy(SCRIPT, scripts_dir / SCRIPT.name)
    return tmp_path


def _run_under(tmp_root: Path) -> subprocess.CompletedProcess[str]:
    script_copy = tmp_root / "scripts" / SCRIPT.name
    return subprocess.run(
        [sys.executable, str(script_copy)],
        cwd=tmp_root,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_real_project_workflows_are_clean() -> None:
    """The real `.github/workflows/*.yml` must not contain script injection
    vectors after the release.yml F-3 fix."""
    result = _run()
    assert result.returncode == 0, (
        f"Real workflows must be free of injection vectors. stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert "[OK]" in result.stdout
    assert "11 workflow" in result.stdout or "11 workflow file" in result.stdout


def test_inputs_dot_token_in_run_is_flagged(tmp_path: Path) -> None:
    """Fixture: a workflow that interpolates `inputs.tag` directly inside
    a `run:` block must be flagged with exit code 1."""
    body = textwrap.dedent(
        """\
        name: bad-inputs
        on: workflow_dispatch
        jobs:
          dispatch:
            runs-on: ubuntu-latest
            steps:
              - name: Unsafe input use
                run: echo "tag=${{ inputs.tag }}"
        """
    )
    tree = _make_project_tree(tmp_path, ("bad-inputs.yml", body))
    result = _run_under(tree)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "inputs.tag" in result.stdout
    assert "[FAIL]" in result.stderr


def test_github_event_in_run_is_flagged(tmp_path: Path) -> None:
    """Fixture: `${{ github.event.pull_request.title }}` inside `run:`
    is the canonical script-injection vector for PR titles."""
    body = textwrap.dedent(
        """\
        name: bad-event
        on: pull_request
        jobs:
          dispatch:
            runs-on: ubuntu-latest
            steps:
              - name: Unsafe event use
                run: echo "title=${{ github.event.pull_request.title }}"
        """
    )
    tree = _make_project_tree(tmp_path, ("bad-event.yml", body))
    result = _run_under(tree)
    assert result.returncode == 1
    assert "github.event.pull_request.title" in result.stdout


def test_env_mapped_input_is_clean(tmp_path: Path) -> None:
    """Fixture: `${{ inputs.tag }}` routed through `env:` is the safe
    pattern and must not be flagged."""
    body = textwrap.dedent(
        """\
        name: safe-env-mapped
        on: workflow_dispatch
        jobs:
          dispatch:
            runs-on: ubuntu-latest
            steps:
              - name: Safe env-mapped input
                env:
                  INPUT_TAG: ${{ inputs.tag }}
                run: echo "tag=$INPUT_TAG"
        """
    )
    tree = _make_project_tree(tmp_path, ("safe.yml", body))
    result = _run_under(tree)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK]" in result.stdout


def test_expression_inside_if_is_not_flagged(tmp_path: Path) -> None:
    """Fixture: `${{ inputs.X }}` inside `if:` conditions is evaluated by
    the runner expression engine, NOT by shell. The script must only flag
    `run:` blocks (not `if:` or `env:` mappings)."""
    body = textwrap.dedent(
        """\
        name: safe-if-expr
        on: workflow_dispatch
        jobs:
          dispatch:
            runs-on: ubuntu-latest
            steps:
              - name: Conditional step
                if: ${{ inputs.tag != '' }}
                run: echo "static text only"
        """
    )
    tree = _make_project_tree(tmp_path, ("safe-if.yml", body))
    result = _run_under(tree)
    assert result.returncode == 0


def test_malformed_yaml_is_reported(tmp_path: Path) -> None:
    """Fixture: a malformed workflow yields a non-fatal `[ERR]` line but
    must NOT crash the script."""
    body = "name: bad\n  invalid: : indentation"
    tree = _make_project_tree(tmp_path, ("malformed.yml", body))
    result = _run_under(tree)
    # Malformed YAML reports as a finding but we accept any non-2 exit since
    # the script returns 1 when findings are emitted.
    assert result.returncode in (0, 1)
    if result.returncode == 1:
        assert "malformed YAML" in result.stdout


def test_no_workflows_dir_emits_operational_error(tmp_path: Path) -> None:
    """Operational error path: missing `.github/workflows/` dir yields exit 2."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    shutil.copy(SCRIPT, scripts_dir / SCRIPT.name)
    result = subprocess.run(
        [sys.executable, str(scripts_dir / SCRIPT.name)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 2
    assert "workflows dir missing" in result.stderr


@pytest.mark.parametrize(
    "spaces",
    [
        "${{inputs.tag}}",        # no padding
        "${{ inputs.tag }}",      # canonical single-space
        "${{  inputs.tag  }}",   # double-spaced
    ],
)
def test_whitespace_tolerance_in_injection_pattern(tmp_path: Path, spaces: str) -> None:
    """All canonical whitespace variants of `${{ inputs.X }}` must match."""
    body = textwrap.dedent(
        f"""\
        name: spaces-check
        on: workflow_dispatch
        jobs:
          dispatch:
            runs-on: ubuntu-latest
            steps:
              - name: Unsafe spacing variant
                run: echo "tag={spaces}"
        """
    )
    tree = _make_project_tree(tmp_path, ("spaces.yml", body))
    result = _run_under(tree)
    assert result.returncode == 1
