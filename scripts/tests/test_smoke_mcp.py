"""Self-tests for `scripts/smoke_mcp_capabilities.py`.

Exercises probe_remote (HEAD-then-GET fallback, HTTP-status-as-alive
semantics, network-error fail path) and probe_local (skip when launcher
absent, alive when timeout window elapses, indeterminate when process
exits 0 fast, fail when process exits non-zero). Stdlib-only mocking
via unittest.mock; no network calls.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODULE_PATH = PROJECT_ROOT / "scripts" / "smoke_mcp_capabilities.py"


def _load_smoke_module() -> Any:
    """Import scripts/smoke_mcp_capabilities.py as a module by file path
    (the script has no __init__ siblings and is not on the Python path
    by default — conftest only exposes scripts/ for relative imports)."""
    spec = importlib.util.spec_from_file_location("smoke_mcp_capabilities", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["smoke_mcp_capabilities"] = module
    spec.loader.exec_module(module)
    return module


smoke = _load_smoke_module()


# ---------------------------------------------------------------------------
# probe_remote
# ---------------------------------------------------------------------------

class _FakeResp:
    """Minimal context-manager mock for urllib.request.urlopen returns."""

    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None


def test_probe_remote_head_success() -> None:
    with mock.patch.object(smoke.urllib.request, "urlopen", return_value=_FakeResp(200)):
        result = smoke.probe_remote("foo", "https://example.test/mcp")
    assert result["status"] == "alive"
    assert result["method"] == "HEAD"
    assert result["http"] == 200


def test_probe_remote_http_error_still_alive() -> None:
    """A 401/403/405 from an auth-gated or method-rejecting endpoint
    still proves the server answered. The probe must mark it `alive`."""
    err = urllib.error.HTTPError("https://example.test/mcp", 401, "Unauthorized", {}, None)
    with mock.patch.object(smoke.urllib.request, "urlopen", side_effect=err):
        result = smoke.probe_remote("foo", "https://example.test/mcp")
    assert result["status"] == "alive"
    assert result["http"] == 401


def test_probe_remote_head_then_get_fallback() -> None:
    """HEAD raising URLError followed by GET succeeding marks alive
    with method='GET' — matches the grep / openai-docs behaviour."""
    responses = [urllib.error.URLError("HEAD blocked"), _FakeResp(405)]
    with mock.patch.object(smoke.urllib.request, "urlopen", side_effect=responses):
        result = smoke.probe_remote("foo", "https://example.test/mcp")
    assert result["status"] == "alive"
    assert result["method"] == "GET"


def test_probe_remote_total_failure() -> None:
    """Both HEAD and GET error → fail."""
    err = urllib.error.URLError("network down")
    with mock.patch.object(smoke.urllib.request, "urlopen", side_effect=err):
        result = smoke.probe_remote("foo", "https://example.test/mcp")
    assert result["status"] == "fail"
    assert "unreachable" in result["error"] or "network down" in result["error"]


def test_probe_remote_rejects_non_https_without_network_call() -> None:
    with mock.patch.object(smoke.urllib.request, "urlopen") as urlopen:
        result = smoke.probe_remote("foo", "file:///etc/passwd")
    urlopen.assert_not_called()
    assert result["status"] == "fail"
    assert "absolute https" in result["error"]


# ---------------------------------------------------------------------------
# probe_local
# ---------------------------------------------------------------------------

def test_probe_local_missing_launcher_is_skip() -> None:
    result = smoke.probe_local("foo", ["/nonexistent/path/to/launcher", "arg"])
    assert result["status"] == "skip"
    assert "not on PATH" in result["reason"]


def test_probe_local_alive_on_timeout() -> None:
    """sleep infinity → still running after window → alive."""
    if not smoke.shutil.which("sleep"):
        pytest.skip("sleep binary not on PATH")
    # Use the smallest possible window for test speed.
    orig_window = smoke.LOCAL_PROBE_WINDOW_SECONDS
    try:
        smoke.LOCAL_PROBE_WINDOW_SECONDS = 0.3
        result = smoke.probe_local("foo", ["sleep", "5"])
    finally:
        smoke.LOCAL_PROBE_WINDOW_SECONDS = orig_window
    assert result["status"] == "alive", result


def test_probe_local_indeterminate_on_clean_fast_exit() -> None:
    """`true` exits 0 immediately — indeterminate (not alive, not fail).
    Documents the 0.10.1 behaviour change."""
    if not smoke.shutil.which("true"):
        pytest.skip("true binary not on PATH")
    result = smoke.probe_local("foo", ["true"])
    assert result["status"] == "indeterminate", result
    assert result["exit_code"] == 0
    assert "exited cleanly" in result.get("reason", "")


def test_probe_local_fail_on_nonzero_exit() -> None:
    """`false` exits 1 immediately — fail."""
    if not smoke.shutil.which("false"):
        pytest.skip("false binary not on PATH")
    result = smoke.probe_local("foo", ["false"])
    assert result["status"] == "fail", result
    assert result["exit_code"] != 0


# ---------------------------------------------------------------------------
# main(): exit codes + JSON envelope
# ---------------------------------------------------------------------------

def test_main_text_mode_returns_exit_0_on_no_failures(capsys: pytest.CaptureFixture[str]) -> None:
    """Mock probe_remote / probe_local to return only `alive` and `skip`
    statuses — main should exit 0."""
    fake_results = [
        {"name": "a", "kind": "remote", "status": "alive", "method": "HEAD", "http": 200, "latency_ms": 5},
        {"name": "b", "kind": "local", "status": "skip", "reason": "launcher 'x' not on PATH"},
    ]
    with mock.patch.object(smoke, "probe_remote", side_effect=lambda n, u: fake_results[0]):
        with mock.patch.object(smoke, "probe_local", side_effect=lambda n, c: fake_results[1]):
            with mock.patch.object(
                sys, "argv", ["smoke_mcp_capabilities.py"]
            ):
                rc = smoke.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "0 failed" in out


def test_main_text_mode_exit_1_on_fail(capsys: pytest.CaptureFixture[str]) -> None:
    """A single fail → exit code 1."""
    with mock.patch.object(
        smoke, "probe_remote", side_effect=lambda n, u: {"name": n, "kind": "remote", "status": "fail", "error": "x"}
    ):
        with mock.patch.object(
            smoke, "probe_local", side_effect=lambda n, c: {"name": n, "kind": "local", "status": "alive"}
        ):
            with mock.patch.object(sys, "argv", ["smoke_mcp_capabilities.py"]):
                rc = smoke.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "[FAIL]" in out


def test_main_json_mode_emits_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    """--json mode emits a valid JSON envelope with required keys."""
    with mock.patch.object(
        smoke, "probe_remote", side_effect=lambda n, u: {"name": n, "kind": "remote", "status": "alive"}
    ):
        with mock.patch.object(
            smoke, "probe_local", side_effect=lambda n, c: {"name": n, "kind": "local", "status": "indeterminate", "exit_code": 0}
        ):
            with mock.patch.object(sys, "argv", ["smoke_mcp_capabilities.py", "--json"]):
                rc = smoke.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert set(payload.keys()) >= {"results", "failed", "indeterminate", "total", "mode"}
    assert payload["failed"] == 0
    assert payload["indeterminate"] >= 1
    assert payload["mode"] == "all"


# ---------------------------------------------------------------------------
# --mode profiles (audit P1-4 closure)
# ---------------------------------------------------------------------------


def test_mode_static_emits_descriptors_without_spawning(capsys: pytest.CaptureFixture[str]) -> None:
    """static mode must NOT call probe_remote / probe_local — it only parses."""
    with mock.patch.object(smoke, "probe_remote") as remote_mock:
        with mock.patch.object(smoke, "probe_local") as local_mock:
            with mock.patch.object(
                sys, "argv", ["smoke_mcp_capabilities.py", "--mode", "static", "--json"]
            ):
                rc = smoke.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["mode"] == "static"
    # Probes are not invoked in static mode.
    remote_mock.assert_not_called()
    local_mock.assert_not_called()
    for r in payload["results"]:
        assert r["status"] == "static"
        assert "profile" in r, r


def test_mode_local_launch_skips_remote_entries(capsys: pytest.CaptureFixture[str]) -> None:
    """local-launch mode only spawns local entries; remote entries are skipped_by_mode."""
    with mock.patch.object(smoke, "probe_remote") as remote_mock:
        with mock.patch.object(
            smoke, "probe_local", side_effect=lambda n, c: {"name": n, "kind": "local", "status": "skip", "reason": "x"}
        ):
            with mock.patch.object(
                sys, "argv", ["smoke_mcp_capabilities.py", "--mode", "local-launch", "--json"]
            ):
                rc = smoke.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["mode"] == "local-launch"
    remote_mock.assert_not_called()
    # Every emitted result is for a local server
    for r in payload["results"]:
        assert r["kind"] == "local"
    assert payload["skipped_by_mode"], (
        "local-launch must mark remote servers as skipped_by_mode"
    )


def test_mode_remote_head_skips_local_entries(capsys: pytest.CaptureFixture[str]) -> None:
    with mock.patch.object(smoke, "probe_local") as local_mock:
        with mock.patch.object(
            smoke, "probe_remote", side_effect=lambda n, u: {"name": n, "kind": "remote", "status": "alive"}
        ):
            with mock.patch.object(
                sys, "argv", ["smoke_mcp_capabilities.py", "--mode", "remote-head", "--json"]
            ):
                rc = smoke.main()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["mode"] == "remote-head"
    local_mock.assert_not_called()
    for r in payload["results"]:
        assert r["kind"] == "remote"
    assert payload["skipped_by_mode"], (
        "remote-head must mark local servers as skipped_by_mode"
    )


def test_mode_all_remains_default_behaviour(capsys: pytest.CaptureFixture[str]) -> None:
    with mock.patch.object(
        smoke, "probe_remote", side_effect=lambda n, u: {"name": n, "kind": "remote", "status": "alive"}
    ):
        with mock.patch.object(
            smoke, "probe_local", side_effect=lambda n, c: {"name": n, "kind": "local", "status": "skip", "reason": "x"}
        ):
            with mock.patch.object(sys, "argv", ["smoke_mcp_capabilities.py", "--json"]):
                rc = smoke.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "all"
    assert rc == 0
    kinds = {r["kind"] for r in payload["results"]}
    assert "remote" in kinds and "local" in kinds


def test_invalid_mode_rejected_by_argparse(capsys: pytest.CaptureFixture[str]) -> None:
    """Argparse choices must reject unknown mode names with exit 2."""
    with mock.patch.object(sys, "argv", ["smoke_mcp_capabilities.py", "--mode", "bogus"]):
        with pytest.raises(SystemExit) as excinfo:
            smoke.main()
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "invalid choice" in err or "usage" in err
