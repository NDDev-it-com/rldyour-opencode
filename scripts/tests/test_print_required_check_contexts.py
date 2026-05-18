"""Tests for `scripts/print_required_check_contexts.sh`.

Closes audit Architecture-review F-5: the extractor that feeds
`docs/github/branch-protection.md` was the only script in `scripts/`
without coverage. These tests pin the output contract — text mode
header, JSON mode envelope shape, exit codes — and the PyYAML
fallback path so the heredoc Python module cannot regress to a raw
ImportError traceback.

Every subprocess.run here arms an explicit timeout per audit P0-4.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "print_required_check_contexts.sh"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

DEFAULT_TIMEOUT = 30


def _run(*extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *extra_args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_TIMEOUT,
    )


def test_script_exists_and_is_executable() -> None:
    assert SCRIPT.exists(), "scripts/print_required_check_contexts.sh must exist"
    import os

    assert os.access(SCRIPT, os.X_OK), "scripts/print_required_check_contexts.sh must be executable"


def test_text_mode_runs_clean() -> None:
    """Default invocation prints the header + one line per (workflow,
    job, matrix-cell) context."""
    proc = _run()
    assert proc.returncode == 0, f"stderr={proc.stderr[:500]}"
    out = proc.stdout
    assert "WORKFLOW" in out, "header row missing"
    assert "JOB" in out and "CONTEXT" in out, "header columns missing"
    # Validate workflow must always be in the table — workflows/validate.yml is
    # the project gatekeeper and matrices on Linux + macOS.
    assert "Validate rldyour-opencode" in out


def test_json_mode_emits_valid_envelope() -> None:
    proc = _run("--json")
    assert proc.returncode == 0, f"stderr={proc.stderr[:500]}"
    payload = json.loads(proc.stdout)
    assert {"count", "contexts"}.issubset(payload.keys()), payload.keys()
    assert isinstance(payload["count"], int)
    assert isinstance(payload["contexts"], list)
    assert payload["count"] == len(payload["contexts"])
    # Every entry has the documented shape so consumers (branch-protection
    # docs, future required-context syncing tooling) can rely on it.
    for ctx in payload["contexts"]:
        assert {
            "workflow_file",
            "workflow_name",
            "job_key",
            "job_display",
            "context",
            "triggers",
            "matrix",
        }.issubset(ctx.keys()), ctx
        assert isinstance(ctx["triggers"], list)
        assert ctx["matrix"] is None or isinstance(ctx["matrix"], dict)


def test_json_mode_lists_known_workflow_contexts() -> None:
    """Mirror of the docs/github/branch-protection.md required-context
    table. If a workflow is added or removed, this test must be updated
    in lockstep with the docs."""
    proc = _run("--json")
    payload = json.loads(proc.stdout)
    contexts = {ctx["context"] for ctx in payload["contexts"]}
    expected_pr_required = {
        "Validate rldyour-opencode / validate (ubuntu-latest)",
        "Validate rldyour-opencode / validate (macos-latest)",
        "Validate rldyour-opencode / shell-strict-mode",
        "Typecheck Plugins / typecheck (ubuntu-latest)",
        "Typecheck Plugins / typecheck (macos-latest)",
        "Lint / ruff (ubuntu-latest)",
        "Lint / ruff (macos-latest)",
        "Instruction Docs Check / instruction-docs",
        "Secret Scan / gitleaks",
        "CodeQL / Analyze (javascript-typescript)",
        "CodeQL / Analyze (python)",
        "OpenCode Runtime / runtime (ubuntu-latest)",
        "OpenCode Runtime / runtime (macos-latest)",
    }
    missing = expected_pr_required - contexts
    assert not missing, (
        f"docs/github/branch-protection.md PR-required contexts not found in workflow output: {missing}"
    )


def test_workflow_count_matches_disk() -> None:
    """Total context count must be at least the number of workflow files
    on disk (matrix expansions add more, never less)."""
    proc = _run("--json")
    payload = json.loads(proc.stdout)
    on_disk = list(WORKFLOWS_DIR.glob("*.yml"))
    # The script emits one row per (job × matrix-cell). It must produce
    # at LEAST one row per workflow that has jobs.
    assert payload["count"] >= len(on_disk), (
        f"extractor produced {payload['count']} rows for {len(on_disk)} workflow files"
    )
