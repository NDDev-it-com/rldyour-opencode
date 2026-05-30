"""Tests for scripts/_check_freshness.py and the deps freshness wrapper.

Network calls are mocked via monkeypatching urllib.request.urlopen so
the suite runs offline (CI runner may have egress filtered).
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

# sys.path setup happens in conftest.py at session start.
import _check_freshness as cf  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WRAPPER_SH = PROJECT_ROOT / "scripts" / "check_deps_freshness.sh"


# ---------- _semver_tuple / _semver_parts ----------


@pytest.mark.parametrize(
    "version,expected",
    [
        ("1.3.0", (1, 3, 0)),
        ("v1.3.0", (1, 3, 0)),
        ("0.0.75", (0, 0, 75)),
        ("2025.12.18", (2025, 12, 18)),
        ("1.3.0-rc1", (1, 3, 0)),
        ("1.3.0.dev0", (1, 3, 0)),
    ],
)
def test_semver_tuple_parses(version: str, expected: tuple[int, int, int]) -> None:
    assert cf._semver_tuple(version) == expected


@pytest.mark.parametrize("version", ["", "system", "latest", "not-a-version", "1.2"])
def test_semver_tuple_returns_none_for_non_semver(version: str) -> None:
    assert cf._semver_tuple(version) is None


@pytest.mark.parametrize(
    "version,expected",
    [
        ("1.3.0", (1, 3, 0, 1)),
        ("v1.3.0", (1, 3, 0, 1)),
        ("1.3.0-rc1", (1, 3, 0, 0)),
        ("1.3.0.dev0", (1, 3, 0, 0)),
        ("1.3.0-alpha.1", (1, 3, 0, 0)),
        ("1.3.0.beta2", (1, 3, 0, 0)),
    ],
)
def test_semver_parts_classifies_stability(
    version: str, expected: tuple[int, int, int, int]
) -> None:
    assert cf._semver_parts(version) == expected


# ---------- classify ----------


def test_classify_current() -> None:
    assert cf.classify("1.3.0", "1.3.0") == "current"


def test_classify_stale() -> None:
    assert cf.classify("1.3.0", "1.4.0") == "stale"


def test_classify_ahead() -> None:
    assert cf.classify("2.0.0", "1.9.9") == "ahead"


def test_classify_unknown_when_latest_none() -> None:
    assert cf.classify("1.3.0", None) == "unknown"


def test_classify_unknown_when_unparseable() -> None:
    assert cf.classify("system", "system") == "current"
    assert cf.classify("1.3.0", "not-semver") == "unknown"


@pytest.mark.parametrize(
    "current,latest,expected",
    [
        ("1.3.0.dev0", "1.3.0", "stale"),
        ("1.3.0-rc1", "1.3.0", "stale"),
        ("1.3.0-alpha.1", "1.3.0", "stale"),
        ("1.3.0", "1.3.0.dev0", "ahead"),
        ("1.3.0", "1.3.0-rc1", "ahead"),
    ],
)
def test_classify_orders_prerelease_below_matching_stable(
    current: str, latest: str, expected: str
) -> None:
    assert cf.classify(current, latest) == expected


# ---------- probe_npm / probe_pypi (mocked) ----------


def _fake_urlopen_factory(payload: dict | None, *, status: int | None = None):
    """Return a callable that monkeypatches urllib.request.urlopen.

    Use payload=None + status=<int> to simulate HTTPError; status=None
    yields a successful 200 response carrying the payload as JSON.
    """
    class _Response:
        def __init__(self, body: bytes) -> None:
            self.body = body
            self.status = 200

        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return self.body

    def _fake(_req, *, timeout=None):  # noqa: ANN001 - mock signature
        if payload is None:
            from urllib.error import HTTPError
            raise HTTPError("u", status or 500, "boom", {}, None)
        return _Response(json.dumps(payload).encode("utf-8"))

    return _fake


def test_probe_npm_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        _fake_urlopen_factory({"version": "2.0.0"}),
    )
    latest, err = cf.probe_npm("@playwright/mcp")
    assert latest == "2.0.0"
    assert err is None


def test_registry_url_validation_rejects_non_https() -> None:
    with pytest.raises(ValueError, match="unexpected registry URL host"):
        cf._validate_registry_url("file:///etc/passwd", allowed_host=cf.NPM_REGISTRY_HOST)


def test_probe_npm_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        _fake_urlopen_factory(None, status=404),
    )
    latest, err = cf.probe_npm("nonexistent")
    assert latest is None
    assert err is not None and "404" in err


def test_probe_pypi_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        _fake_urlopen_factory({"info": {"version": "1.163.0"}}),
    )
    latest, err = cf.probe_pypi("semgrep")
    assert latest == "1.163.0"
    assert err is None


def test_probe_pypi_malformed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing `info.version` must report an error string, not raise."""
    monkeypatch.setattr(
        "urllib.request.urlopen",
        _fake_urlopen_factory({"info": {}}),
    )
    latest, err = cf.probe_pypi("weird")
    assert latest is None
    assert err == "unexpected response shape"


# ---------- main() envelope ----------


def _run_main_with_pins(
    monkeypatch: pytest.MonkeyPatch,
    pins: list[dict],
    npm_versions: dict[str, str | None],
    pypi_versions: dict[str, str | None],
    capsys: pytest.CaptureFixture[str],
    *,
    extra_argv: list[str] | None = None,
) -> tuple[int, dict]:
    """Run cf.main() with stdin set to {pins: pins} and probe_npm /
    probe_pypi monkeypatched to return entries from the version maps.
    """
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"pins": pins})))
    monkeypatch.setattr(sys, "argv", ["_check_freshness.py", *(extra_argv or [])])

    def _fake_npm(name: str) -> tuple[str | None, str | None]:
        if name not in npm_versions:
            return None, "missing fixture"
        return npm_versions[name], None

    def _fake_pypi(name: str) -> tuple[str | None, str | None]:
        if name not in pypi_versions:
            return None, "missing fixture"
        return pypi_versions[name], None

    monkeypatch.setattr(cf, "probe_npm", _fake_npm)
    monkeypatch.setattr(cf, "probe_pypi", _fake_pypi)

    exit_code = cf.main()
    out = capsys.readouterr().out
    envelope = json.loads(out)
    return exit_code, envelope


def test_main_all_current_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pins = [
        {"kind": "npm", "server": "x", "name": "x-pkg", "version": "1.0.0"},
        {"kind": "pypi", "server": "y", "name": "y-pkg", "version": "1.0.0"},
    ]
    code, env = _run_main_with_pins(
        monkeypatch,
        pins,
        npm_versions={"x-pkg": "1.0.0"},
        pypi_versions={"y-pkg": "1.0.0"},
        capsys=capsys,
    )
    assert code == 0
    assert env["stale"] == 0
    assert env["errors"] == 0
    assert all(p["status"] == "current" for p in env["pins"])


def test_main_stale_exits_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pins = [{"kind": "npm", "server": "x", "name": "x-pkg", "version": "1.0.0"}]
    code, env = _run_main_with_pins(
        monkeypatch,
        pins,
        npm_versions={"x-pkg": "1.2.0"},
        pypi_versions={},
        capsys=capsys,
    )
    assert code == 1
    assert env["stale"] == 1
    assert env["pins"][0]["status"] == "stale"
    assert env["pins"][0]["latest"] == "1.2.0"


def test_main_strict_with_errors_exits_two(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pins = [{"kind": "npm", "server": "x", "name": "missing-pkg", "version": "1.0.0"}]
    code, env = _run_main_with_pins(
        monkeypatch,
        pins,
        npm_versions={},
        pypi_versions={},
        capsys=capsys,
        extra_argv=["--strict"],
    )
    assert code == 2
    assert env["errors"] == 1


def test_main_pypi_stale_classified(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Parity with the npm stale path: a PyPI pin that lags must be
    classified stale, surface in `latest`, and bump the envelope
    `stale` counter. Closes reviewer 0.11.0 finding 'stale path only
    tests npm flavor'."""
    pins = [{"kind": "pypi", "server": "y", "name": "y-pkg", "version": "1.0.0"}]
    code, env = _run_main_with_pins(
        monkeypatch,
        pins,
        npm_versions={},
        pypi_versions={"y-pkg": "2.0.0"},
        capsys=capsys,
    )
    assert code == 1
    assert env["stale"] == 1
    assert env["pins"][0]["status"] == "stale"
    assert env["pins"][0]["latest"] == "2.0.0"
    assert env["pins"][0]["source"] == "pypi"


def test_main_npm_ahead_classified(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An `ahead` classification (local pin newer than upstream stable)
    must NOT count as stale and must NOT exit non-zero. Future regression
    in semver comparison would otherwise downgrade an ahead pin to
    stale."""
    pins = [{"kind": "npm", "server": "x", "name": "x-pkg", "version": "2.0.0"}]
    code, env = _run_main_with_pins(
        monkeypatch,
        pins,
        npm_versions={"x-pkg": "1.9.9"},
        pypi_versions={},
        capsys=capsys,
    )
    assert code == 0
    assert env["stale"] == 0
    assert env["pins"][0]["status"] == "ahead"


def test_main_dart_kind_is_skipped(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pins = [{"kind": "dart", "server": "dart-flutter", "name": "dart-sdk", "version": "system"}]
    code, env = _run_main_with_pins(
        monkeypatch,
        pins,
        npm_versions={},
        pypi_versions={},
        capsys=capsys,
    )
    assert code == 0
    assert env["pins"][0]["status"] == "skip"
    assert env["pins"][0]["source"] == "dart"


# ---------- check_deps_freshness.sh wrapper ----------


def test_wrapper_default_emits_pin_report() -> None:
    """Bare invocation must still print the pin report (no --check-freshness)."""
    result = subprocess.run(
        ["bash", str(WRAPPER_SH)],
        check=True,
        capture_output=True,
        cwd=str(PROJECT_ROOT),
        timeout=30,
    )
    out = result.stdout.decode("utf-8")
    assert "Pinned dependencies" in out
    assert "Pass --check-freshness" in out


def test_wrapper_json_envelope_shape() -> None:
    result = subprocess.run(
        ["bash", str(WRAPPER_SH), "--json"],
        check=True,
        capture_output=True,
        cwd=str(PROJECT_ROOT),
        timeout=30,
    )
    env = json.loads(result.stdout.decode("utf-8"))
    assert "pins" in env
    assert "count" in env
    assert env["count"] == len(env["pins"])
    assert env["count"] >= 1


def test_wrapper_unknown_flag_returns_2() -> None:
    result = subprocess.run(
        ["bash", str(WRAPPER_SH), "--no-such-flag"],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
        timeout=10,
    )
    assert result.returncode == 2
    assert b"unknown flag" in result.stderr
