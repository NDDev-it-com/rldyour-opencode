"""Unit tests for scripts/_validate_helpers.py.

Run via `python3 -m pytest scripts/tests/ -v` or as part of CI.

Tests cover the error branches that bash scripts/validate_config.sh exercises
on the real project state. Each test writes a tiny fixture into a tmp path
and asserts the validator's exit code and stdout.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make scripts/ importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _validate_helpers as vh  # noqa: E402


# ---------- opencode.json shape ----------


def test_opencode_json_valid(tmp_path: Path) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text('{"model": "anthropic/claude-sonnet-4-6"}', encoding="utf-8")
    assert vh.validate_opencode_json(cfg) == 0


def test_opencode_json_missing_model(tmp_path: Path) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text("{}", encoding="utf-8")
    assert vh.validate_opencode_json(cfg) == 1


def test_opencode_json_rejects_command_block(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text(
        '{"model": "anthropic/claude-sonnet-4-6", "command": {"test": {"description": "t"}}}',
        encoding="utf-8",
    )
    assert vh.validate_opencode_json(cfg) == 1
    captured = capsys.readouterr()
    assert "must not contain a 'command' block" in captured.out


def test_opencode_json_invalid_agent_mode(tmp_path: Path) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text(
        '{"model": "x", "agent": {"foo": {"mode": "weird"}}}',
        encoding="utf-8",
    )
    assert vh.validate_opencode_json(cfg) == 1


def test_opencode_json_invalid_permission_edit(tmp_path: Path) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text(
        '{"model": "x", "agent": {"foo": {"permission": {"edit": "maybe"}}}}',
        encoding="utf-8",
    )
    assert vh.validate_opencode_json(cfg) == 1


def test_opencode_json_invalid_json(tmp_path: Path) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text("{not json", encoding="utf-8")
    assert vh.validate_opencode_json(cfg) == 1


def test_opencode_json_handles_bom(tmp_path: Path) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_bytes(b'\xef\xbb\xbf{"model": "anthropic/claude-sonnet-4-6"}')
    assert vh.validate_opencode_json(cfg) == 0


# ---------- VERSION ----------


def test_version_valid_semver(tmp_path: Path) -> None:
    v = tmp_path / "VERSION"
    v.write_text("1.2.3\n", encoding="utf-8")
    assert vh.validate_version(v) == 0


def test_version_rejects_prerelease(tmp_path: Path) -> None:
    v = tmp_path / "VERSION"
    v.write_text("1.0.0-beta\n", encoding="utf-8")
    assert vh.validate_version(v) == 1


def test_version_rejects_empty(tmp_path: Path) -> None:
    v = tmp_path / "VERSION"
    v.write_text("\n", encoding="utf-8")
    assert vh.validate_version(v) == 1


# ---------- Skills ----------


def _write_skill(root: Path, name: str, body: str) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(body, encoding="utf-8")
    return d


def test_skill_valid_inline_description(tmp_path: Path) -> None:
    d = _write_skill(
        tmp_path,
        "my-skill",
        "---\nname: my-skill\ndescription: A short description.\n---\nbody",
    )
    assert vh.validate_skill(d) == 0


def test_skill_valid_block_scalar_description(tmp_path: Path) -> None:
    d = _write_skill(
        tmp_path,
        "block-skill",
        "---\nname: block-skill\ndescription: |\n  Multi-line block scalar description\n  that spans several lines.\n---\nbody",
    )
    assert vh.validate_skill(d) == 0


def test_skill_name_mismatch(tmp_path: Path) -> None:
    d = _write_skill(
        tmp_path,
        "my-skill",
        "---\nname: other\ndescription: x\n---\n",
    )
    assert vh.validate_skill(d) > 0


def test_skill_missing_frontmatter(tmp_path: Path) -> None:
    d = _write_skill(tmp_path, "my-skill", "no frontmatter here")
    assert vh.validate_skill(d) > 0


def test_skill_name_not_kebab(tmp_path: Path) -> None:
    d = _write_skill(
        tmp_path,
        "BadName",
        "---\nname: BadName\ndescription: x\n---\n",
    )
    assert vh.validate_skill(d) > 0


def test_skill_description_too_long(tmp_path: Path) -> None:
    long = "a" * 1025
    d = _write_skill(
        tmp_path,
        "ls",
        f"---\nname: ls\ndescription: {long}\n---\n",
    )
    assert vh.validate_skill(d) > 0


def test_skill_duplicate_key(tmp_path: Path) -> None:
    d = _write_skill(
        tmp_path,
        "dup",
        "---\nname: dup\nname: other\ndescription: x\n---\n",
    )
    assert vh.validate_skill(d) > 0


# ---------- Agents ----------


def _write_agent(root: Path, name: str, body: str) -> Path:
    p = root / f"{name}.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_agent_valid_color_hex(tmp_path: Path) -> None:
    p = _write_agent(
        tmp_path,
        "a",
        '---\ndescription: x\nmode: subagent\ncolor: "#3b82f6"\n---\n',
    )
    assert vh.validate_agent(p) == 0


def test_agent_valid_color_enum(tmp_path: Path) -> None:
    for v in ("primary", "secondary", "accent", "success", "warning", "error", "info"):
        p = _write_agent(
            tmp_path,
            f"a-{v}",
            f"---\ndescription: x\nmode: subagent\ncolor: {v}\n---\n",
        )
        assert vh.validate_agent(p) == 0, f"valid color {v} should pass"


def test_agent_rejects_named_color(tmp_path: Path) -> None:
    p = _write_agent(
        tmp_path,
        "bad-color",
        "---\ndescription: x\nmode: subagent\ncolor: blue\n---\n",
    )
    assert vh.validate_agent(p) > 0


def test_agent_invalid_mode(tmp_path: Path) -> None:
    p = _write_agent(
        tmp_path,
        "bad-mode",
        "---\ndescription: x\nmode: superuser\n---\n",
    )
    assert vh.validate_agent(p) > 0


def test_agent_block_scalar_description(tmp_path: Path) -> None:
    p = _write_agent(
        tmp_path,
        "rye",
        "---\ndescription: |\n  Long block-scalar description for the agent.\nmode: subagent\n---\n",
    )
    assert vh.validate_agent(p) == 0


def test_agent_missing_frontmatter(tmp_path: Path) -> None:
    p = _write_agent(tmp_path, "naked", "no frontmatter")
    assert vh.validate_agent(p) > 0


# ---------- Commands ----------


def test_command_valid(tmp_path: Path) -> None:
    p = tmp_path / "c.md"
    p.write_text('---\ndescription: "do thing"\nagent: build\n---\nbody\n', encoding="utf-8")
    assert vh.validate_command(p) == 0


def test_command_missing_description(tmp_path: Path) -> None:
    p = tmp_path / "c.md"
    p.write_text("---\nagent: build\n---\nbody\n", encoding="utf-8")
    assert vh.validate_command(p) > 0


# ---------- CLI dispatch ----------


def test_main_unknown_command_returns_2(tmp_path: Path) -> None:
    assert vh.main(["_validate_helpers.py", "nonsense", str(tmp_path)]) == 2


def test_main_insufficient_args_returns_2() -> None:
    assert vh.main(["_validate_helpers.py", "opencode_json"]) == 2
