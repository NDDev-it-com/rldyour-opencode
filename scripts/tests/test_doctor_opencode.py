"""Integration tests for `scripts/doctor_opencode.py` (Python core).

The 2026-05-17 external audit (P0-3) found that the legacy bash doctor
(`scripts/doctor_opencode.sh`, 306 lines of shell + heredoc Python) was
not deterministic — invocations could pass 25 s without completing,
and several subprocess calls had no `timeout=`. The Python rewrite
replaces the entire core with timeout-safe checks that emit a structured
result envelope (`{check, status, duration_ms, details}`) consumable by
CI gates.

The shell wrapper (`scripts/doctor_opencode.sh`) is now a thin
`exec python3 scripts/doctor_opencode.py "$@"` adapter so existing
operator muscle memory (`bash scripts/doctor_opencode.sh`) keeps
working unchanged.

These tests pin the Python contract:
- granular `--check` selection,
- text and JSON output modes,
- per-check timeout enforcement,
- exit-code semantics (0/1/2/3),
- bash wrapper delegates to the Python core,
- every subprocess invocation arms an explicit `timeout=`.

Every `subprocess.run` in this file has an explicit `timeout=` argument
per audit P0-4 (no test may rely on an unbounded subprocess).
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCTOR_PY = REPO_ROOT / "scripts" / "doctor_opencode.py"
DOCTOR_SH = REPO_ROOT / "scripts" / "doctor_opencode.sh"

DEFAULT_SUBPROCESS_TIMEOUT = 90


def _ansi_strip(text: str) -> str:
    """Strip ANSI color codes from doctor output for stable assertions."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _strip_timings(text: str) -> str:
    """Replace `(NNNms)` timing suffixes with a placeholder so two runs can
    be compared without the duration noise. doctor.py records wall-clock
    per check, which is naturally non-deterministic on a shared runner."""
    return re.sub(r"\(\d+ms\)", "(_ms)", text)


# ---------------------------------------------------------------------------
# Structural contract
# ---------------------------------------------------------------------------


def test_doctor_python_core_is_present() -> None:
    """Audit P0-3 closure: the Python core is the source of truth."""
    assert DOCTOR_PY.exists(), "scripts/doctor_opencode.py must exist (Python core)"
    head = DOCTOR_PY.read_text(encoding="utf-8")[:200]
    assert head.startswith("#!/usr/bin/env python3"), (
        "doctor_opencode.py must start with the python3 shebang"
    )


def test_shell_wrapper_delegates_to_python_core() -> None:
    """Audit P0-3 closure: the bash wrapper must not contain its own logic."""
    text = DOCTOR_SH.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash"), "wrapper must keep env-bash shebang"
    assert "set -euo pipefail" in text
    # The wrapper is intentionally tiny — an exec line that hands off to the
    # Python core. If it grows past ~15 lines, the audit invariant is broken.
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert len(lines) <= 6, (
        f"doctor_opencode.sh wrapper grew past the expected size ({len(lines)} non-comment "
        f"lines). The Python core owns every check; the wrapper must stay a thin exec adapter."
    )
    assert "exec python3" in text and "doctor_opencode.py" in text, (
        "doctor_opencode.sh must exec the Python core (no inline logic)"
    )


def test_doctor_py_arms_per_subprocess_timeout() -> None:
    """Audit P0-3 closure: every subprocess.run in the doctor must specify a timeout.

    Uses AST traversal so multi-line `subprocess.run(...)` calls are
    matched correctly. A naive regex like `subprocess\\.run\\([^)]*\\)`
    truncates at the first `)` inside the argv list and produces a
    false positive on the timeout-bearing call that follows it.
    """
    src = DOCTOR_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)
    runs: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "run"
            and isinstance(func.value, ast.Name)
            and func.value.id == "subprocess"
        ):
            runs.append(node)
    assert runs, "doctor_opencode.py is expected to use subprocess.run"
    missing = [call for call in runs if not any(k.arg == "timeout" for k in call.keywords)]
    assert not missing, (
        f"doctor_opencode.py has {len(missing)} subprocess.run call(s) without "
        f"timeout=:\n{ast.unparse(missing[0])[:200]}"
    )


def test_doctor_py_has_total_timeout_argument() -> None:
    """Wall-clock guard against the legacy 'hangs past 25 s' regression."""
    src = DOCTOR_PY.read_text(encoding="utf-8")
    assert "--total-timeout" in src, "doctor_opencode.py must expose --total-timeout"
    assert "DEFAULT_TOTAL_TIMEOUT_SECONDS" in src, (
        "doctor_opencode.py must define a named default total timeout"
    )


# ---------------------------------------------------------------------------
# Runtime invocation
# ---------------------------------------------------------------------------


def _run_doctor(*extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(DOCTOR_PY), *extra_args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_SUBPROCESS_TIMEOUT,
    )


def _run_doctor_via_wrapper(*extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(DOCTOR_SH), *extra_args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=DEFAULT_SUBPROCESS_TIMEOUT,
    )


def test_doctor_text_mode_runs_clean() -> None:
    proc = _run_doctor()
    assert proc.returncode in (0, 1), (
        f"doctor unexpected exit={proc.returncode}\nstderr={proc.stderr[:500]}"
    )
    text = _ansi_strip(proc.stdout)
    assert "rldyour-opencode Doctor" in text
    assert re.search(r"ok=\d+\s+warn=\d+\s+fail=\d+", text), text[:400]


def test_doctor_json_mode_emits_valid_envelope() -> None:
    proc = _run_doctor("--format", "json")
    assert proc.returncode in (0, 1), proc.stderr[:500]
    payload = json.loads(proc.stdout)
    assert "results" in payload and isinstance(payload["results"], list)
    assert "summary" in payload and isinstance(payload["summary"], dict)
    for r in payload["results"]:
        assert {"check", "status", "duration_ms", "details"}.issubset(r.keys()), r
        assert r["status"] in {"ok", "warn", "fail", "skip", "info", "timeout"}, r
        assert isinstance(r["duration_ms"], int) and r["duration_ms"] >= 0
        assert isinstance(r["details"], list)


def test_doctor_check_subset_runs_only_requested_checks() -> None:
    """`--check config plugins` must run exactly the two named checks."""
    proc = _run_doctor("--check", "config", "plugins", "--format", "json")
    assert proc.returncode in (0, 1), proc.stderr[:500]
    payload = json.loads(proc.stdout)
    names = {r["check"] for r in payload["results"]}
    assert names == {"config.opencode_json", "plugins.index"}, (
        f"--check subset drift; got {names}"
    )


def test_doctor_invalid_check_rejected() -> None:
    proc = _run_doctor("--check", "nonexistent", "--format", "json")
    # argparse rejects unknown choices with exit 2 and a usage line.
    assert proc.returncode == 2, proc.stderr[:500]
    assert "invalid choice" in proc.stderr or "usage:" in proc.stderr


def test_wrapper_output_matches_python_core() -> None:
    """The bash wrapper must produce identical text output to a direct
    Python invocation — that is the contract of a thin exec adapter.

    `(NNNms)` per-check timings are stripped before comparison since
    they vary naturally between two consecutive runs and would
    otherwise turn this assertion into a flaky test."""
    direct = _run_doctor()
    wrapped = _run_doctor_via_wrapper()
    assert direct.returncode == wrapped.returncode, (
        f"return codes differ: python={direct.returncode} bash={wrapped.returncode}"
    )
    normalised_direct = _strip_timings(_ansi_strip(direct.stdout))
    normalised_wrap = _strip_timings(_ansi_strip(wrapped.stdout))
    assert normalised_direct == normalised_wrap


def test_doctor_total_timeout_short_value_completes_quickly() -> None:
    """`--total-timeout 5` must complete in <30 s wall-clock even if some
    checks would otherwise have slow subprocess calls. This proves the
    wall-clock deadline is enforced (audit P0-3 closure)."""
    import time

    started = time.monotonic()
    proc = _run_doctor("--total-timeout", "5", "--format", "json")
    elapsed = time.monotonic() - started
    assert proc.returncode in (0, 1, 3), (
        f"unexpected exit={proc.returncode}, stderr={proc.stderr[:500]}"
    )
    assert elapsed < 30, (
        f"doctor with --total-timeout=5 ran {elapsed:.1f}s; deadline not enforced"
    )


def test_doctor_baseline_check_passes_when_in_flight_present() -> None:
    """When the baseline-consistency in-flight feature is present, the
    `baseline` check must pass (P0-1 closure verification)."""
    baseline_script = REPO_ROOT / "scripts" / "check_baseline_consistency.py"
    if not baseline_script.exists():
        pytest.skip("baseline script absent; nothing to gate")
    proc = _run_doctor("--check", "baseline", "--format", "json")
    payload = json.loads(proc.stdout)
    assert len(payload["results"]) == 1
    r = payload["results"][0]
    assert r["check"] == "config.baseline"
    assert r["status"] in {"ok", "warn", "skip"}, (
        f"baseline check unexpectedly {r['status']!r}; details={r['details']}"
    )
