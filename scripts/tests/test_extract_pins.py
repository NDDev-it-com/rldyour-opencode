"""Unit tests for scripts/_extract_pins.py.

Cover happy path (real opencode.json shape) plus the regression cases
flagged by the verification reviewer: empty mcp, malformed JSON,
missing version, PyPI package name with a dot.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# sys.path setup via conftest.py
import _extract_pins as ep


def _write(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "opencode.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_empty_mcp_returns_no_pins(tmp_path: Path) -> None:
    cfg = _write(tmp_path, {"model": "x"})
    assert ep.extract_pins(cfg) == []


def test_remote_servers_skipped(tmp_path: Path) -> None:
    cfg = _write(tmp_path, {
        "model": "x",
        "mcp": {"remote": {"type": "remote", "url": "https://example.com"}},
    })
    assert ep.extract_pins(cfg) == []


def test_bunx_scoped_npm_pin(tmp_path: Path) -> None:
    cfg = _write(tmp_path, {
        "model": "x",
        "mcp": {"foo": {"type": "local", "command": ["bunx", "@scope/pkg@1.2.3", "--flag"]}},
    })
    pins = ep.extract_pins(cfg)
    assert pins == [{"kind": "npm", "server": "foo", "name": "@scope/pkg", "version": "1.2.3"}]


def test_bunx_unscoped_npm_pin(tmp_path: Path) -> None:
    cfg = _write(tmp_path, {
        "model": "x",
        "mcp": {"bar": {"type": "local", "command": ["bunx", "shadcn@4.8.2", "mcp"]}},
    })
    pins = ep.extract_pins(cfg)
    assert pins == [{"kind": "npm", "server": "bar", "name": "shadcn", "version": "4.8.2"}]


def test_uvx_pypi_pin(tmp_path: Path) -> None:
    cfg = _write(tmp_path, {
        "model": "x",
        "mcp": {"sem": {"type": "local", "command": ["uvx", "--from", "semgrep==1.162.0", "semgrep", "mcp"]}},
    })
    pins = ep.extract_pins(cfg)
    assert pins == [{"kind": "pypi", "server": "sem", "name": "semgrep", "version": "1.162.0"}]


def test_uvx_pypi_pin_with_dot_in_name(tmp_path: Path) -> None:
    """Verification reviewer F-1: names like `zope.interface` must be accepted."""
    cfg = _write(tmp_path, {
        "model": "x",
        "mcp": {"zope": {"type": "local", "command": ["uvx", "--from", "zope.interface==5.4.0", "zope-interface-cli"]}},
    })
    pins = ep.extract_pins(cfg)
    assert pins == [{"kind": "pypi", "server": "zope", "name": "zope.interface", "version": "5.4.0"}]


def test_dart_pin(tmp_path: Path) -> None:
    cfg = _write(tmp_path, {
        "model": "x",
        "mcp": {"d": {"type": "local", "command": ["dart", "mcp-server"]}},
    })
    pins = ep.extract_pins(cfg)
    assert pins == [{"kind": "dart", "server": "d", "name": "dart-sdk", "version": "system"}]


def test_local_without_command_skipped(tmp_path: Path) -> None:
    cfg = _write(tmp_path, {
        "model": "x",
        "mcp": {"local-naked": {"type": "local"}},
    })
    assert ep.extract_pins(cfg) == []


def test_malformed_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "opencode.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        ep.extract_pins(p)


def test_main_emits_envelope(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = _write(tmp_path, {
        "model": "x",
        "mcp": {"foo": {"type": "local", "command": ["bunx", "pkg@1.0.0"]}},
    })
    exit_code = ep.main(["_extract_pins.py", str(cfg)])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "count": 1,
        "pins": [{"kind": "npm", "server": "foo", "name": "pkg", "version": "1.0.0"}],
    }


def test_main_rejects_missing_path() -> None:
    assert ep.main(["_extract_pins.py", "/no/such/path"]) == 2


def test_main_insufficient_args_returns_2() -> None:
    assert ep.main(["_extract_pins.py"]) == 2
