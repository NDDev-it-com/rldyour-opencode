"""Unit tests for scripts/_validate_helpers.py.

Run via `python3 -m pytest scripts/tests/ -v` or as part of CI.

Tests cover the error branches that bash scripts/validate_config.sh exercises
on the real project state. Each test writes a tiny fixture into a tmp path
and asserts the validator's exit code and stdout.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# sys.path setup happens in conftest.py at session start.
import _validate_helpers as vh


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


def test_opencode_json_rejects_missing_absolute_shell(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text('{"model": "x", "shell": "/definitely/missing/shell"}', encoding="utf-8")
    assert vh.validate_opencode_json(cfg) == 1
    captured = capsys.readouterr()
    assert "shell absolute path does not exist" in captured.out


def test_opencode_json_accepts_resolvable_shell_command(tmp_path: Path) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text('{"model": "x", "shell": "sh"}', encoding="utf-8")
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


def test_skill_duplicate_quoted_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = _write_skill(
        tmp_path,
        "dup-quoted",
        '---\n"name": dup-quoted\n"name": other\ndescription: x\n---\n',
    )
    assert vh.validate_skill(d) > 0
    captured = capsys.readouterr()
    assert "duplicate top-level key 'name'" in captured.out


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


def test_agent_duplicate_scan_allows_nested_mappings(tmp_path: Path) -> None:
    p = _write_agent(
        tmp_path,
        "nested-permission",
        "---\n"
        "description: x\n"
        "mode: subagent\n"
        "permission:\n"
        "  bash:\n"
        "    git diff: allow\n"
        "  edit: deny\n"
        "---\n",
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


# ---------- Permission keys (v1.15.x canonical set) ----------


def test_canonical_permission_keys_has_expected_size() -> None:
    """v1.15.13 canonical set has 17 keys (verified via built-in customize-opencode skill)."""
    assert len(vh.CANONICAL_PERMISSION_KEYS) == 17


def test_canonical_permission_keys_includes_v1_15_3_set() -> None:
    """Mirror the canonical set from `opencode debug skill` built-in customize-opencode."""
    expected = {
        "read", "edit", "glob", "grep", "list", "bash", "task",
        "external_directory", "todowrite", "question", "webfetch", "websearch",
        "repo_clone", "repo_overview", "lsp", "doom_loop", "skill",
    }
    assert vh.CANONICAL_PERMISSION_KEYS == expected


def test_canonical_permission_keys_excludes_codesearch() -> None:
    """`codesearch` was removed between v1.14.48 and v1.15.3; do not reintroduce."""
    assert "codesearch" not in vh.CANONICAL_PERMISSION_KEYS


def test_opencode_json_accepts_canonical_top_level_permission(tmp_path: Path) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text(
        '{"model": "x", "permission": {"edit": "allow", "bash": "allow", "lsp": "allow"}}',
        encoding="utf-8",
    )
    assert vh.validate_opencode_json(cfg) == 0


def test_opencode_json_rejects_codesearch_permission_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text(
        '{"model": "x", "permission": {"codesearch": "allow"}}',
        encoding="utf-8",
    )
    assert vh.validate_opencode_json(cfg) == 1
    captured = capsys.readouterr()
    assert "codesearch" in captured.out
    assert "unknown permission key" in captured.out


def test_opencode_json_rejects_pascalcase_permission_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Mirrors sst/opencode#15507 — runtime silently accepts unknown keys; we don't."""
    cfg = tmp_path / "opencode.json"
    cfg.write_text(
        '{"model": "x", "permission": {"Edit": "allow"}}',
        encoding="utf-8",
    )
    assert vh.validate_opencode_json(cfg) == 1
    captured = capsys.readouterr()
    assert "'Edit'" in captured.out


def test_opencode_json_rejects_agent_unknown_permission_key(tmp_path: Path) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text(
        '{"model": "x", "agent": {"foo": {"permission": {"unknown_key": "allow"}}}}',
        encoding="utf-8",
    )
    assert vh.validate_opencode_json(cfg) == 1


def test_opencode_json_accepts_all_mode(tmp_path: Path) -> None:
    """v1.15.x agent.mode accepts `all` (per built-in customize-opencode skill)."""
    cfg = tmp_path / "opencode.json"
    cfg.write_text(
        '{"model": "x", "agent": {"foo": {"mode": "all"}}}',
        encoding="utf-8",
    )
    assert vh.validate_opencode_json(cfg) == 0


def test_yaml_block_child_keys_simple() -> None:
    fm = "permission:\n  edit: allow\n  bash: ask\n"
    assert vh._yaml_block_child_keys(fm, "permission") == ["edit", "bash"]


def test_yaml_block_child_keys_nested_skipped() -> None:
    fm = """permission:
  edit: allow
  bash:
    "git diff": allow
    "*": ask
  read: allow
"""
    # Nested keys under `bash` must NOT appear at the top of `permission`.
    assert vh._yaml_block_child_keys(fm, "permission") == ["edit", "bash", "read"]


def test_yaml_block_child_keys_missing_returns_empty() -> None:
    fm = "description: x\nmode: subagent\n"
    assert vh._yaml_block_child_keys(fm, "permission") == []


def test_yaml_block_child_keys_quoted_key() -> None:
    fm = 'permission:\n  "external_directory": allow\n  read: allow\n'
    assert vh._yaml_block_child_keys(fm, "permission") == ["external_directory", "read"]


def test_agent_rejects_codesearch_permission_in_frontmatter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = _write_agent(
        tmp_path,
        "stale",
        "---\ndescription: x\nmode: subagent\npermission:\n  codesearch: allow\n---\n",
    )
    assert vh.validate_agent(p) > 0
    captured = capsys.readouterr()
    assert "codesearch" in captured.out


def test_agent_accepts_all_canonical_permission_keys_in_frontmatter(tmp_path: Path) -> None:
    """Every key in CANONICAL_PERMISSION_KEYS must be accepted in a real agent file."""
    body_lines = ["---", "description: x", "mode: subagent", "permission:"]
    for key in sorted(vh.CANONICAL_PERMISSION_KEYS):
        body_lines.append(f"  {key}: allow")
    body_lines.append("---")
    p = _write_agent(tmp_path, "fully-permissioned", "\n".join(body_lines) + "\n")
    assert vh.validate_agent(p) == 0


def test_agent_accepts_nested_bash_pattern_permission(tmp_path: Path) -> None:
    """Real reviewer-agent shape: bash with nested glob patterns must pass."""
    body = (
        "---\n"
        "description: x\n"
        "mode: subagent\n"
        "permission:\n"
        "  edit: deny\n"
        "  bash:\n"
        '    "*": ask\n'
        "    git diff: allow\n"
        "  read: allow\n"
        "---\n"
    )
    p = _write_agent(tmp_path, "reviewer-shape", body)
    assert vh.validate_agent(p) == 0


# ---------- 0.11.0 strict-YAML extension ----------


def test_opencode_json_missing_file_returns_err(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """validate_opencode_json must report a deterministic ERR line on a
    missing manifest, not raise an unhandled FileNotFoundError. Closes
    audit finding 4MUSTHAVE P1 'validate_opencode_json catches only
    JSONDecodeError'."""
    cfg = tmp_path / "does-not-exist.json"
    assert vh.validate_opencode_json(cfg) == 1
    captured = capsys.readouterr()
    assert "file not found" in captured.out


def test_agent_mode_all_accepted(tmp_path: Path) -> None:
    """OpenCode v1.15.x docs (https://opencode.ai/docs/agents) allow
    mode: primary | subagent | all. The validator must accept `all`
    alongside primary/subagent so a future config using mode: all does
    not trip a false-negative."""
    p = _write_agent(tmp_path, "all-mode", "---\ndescription: x\nmode: all\n---\n")
    assert vh.validate_agent(p) == 0


def test_agent_yaml_unquoted_colon_in_description_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The 0.10.1 regex parser silently accepted an unquoted scalar
    containing a second colon (the actual reviewer-agent failure mode).
    The 0.11.0 yaml.safe_load parser must reject it as
    'mapping values are not allowed here'."""
    p = _write_agent(
        tmp_path,
        "broken",
        "---\ndescription: Orchestrated review: notes\nmode: subagent\n---\n",
    )
    assert vh.validate_agent(p) > 0
    captured = capsys.readouterr()
    assert "YAML parse error" in captured.out


def test_skill_yaml_invalid_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Skill validator must also surface a real YAML parse error rather
    than silently passing on broken frontmatter (the regex parser used
    to accept this)."""
    skill_dir = tmp_path / "broken-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: broken-skill\ndescription: One: two: three\n---\nbody\n",
        encoding="utf-8",
    )
    assert vh.validate_skill(skill_dir) > 0
    captured = capsys.readouterr()
    assert "YAML parse error" in captured.out


def test_skill_forbidden_field_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SKILL frontmatter must not carry Claude Code / Codex residue
    fields per AGENTS.md skill rules. The 0.10.1 validator silently
    accepted them; 0.11.0 must explicitly reject."""
    skill_dir = tmp_path / "tainted-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: tainted-skill\n"
        "description: a valid description with enough length for the gate\n"
        "model: should-not-be-here\n"
        "allowed-tools: should-not-be-here\n"
        "---\n",
        encoding="utf-8",
    )
    assert vh.validate_skill(skill_dir) > 0
    captured = capsys.readouterr()
    assert "forbidden skill frontmatter field" in captured.out


def test_command_yaml_invalid_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Command validator parity: yaml.safe_load failures must surface
    as a structured ERR line."""
    p = tmp_path / "bad-cmd.md"
    p.write_text(
        "---\ndescription: Run: do something\nagent: build\n---\nbody\n",
        encoding="utf-8",
    )
    assert vh.validate_command(p) > 0
    captured = capsys.readouterr()
    assert "YAML parse error" in captured.out


def test_agent_non_dict_yaml_root_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The frontmatter root MUST be a YAML mapping. A list / scalar root
    (legal YAML, but not the agent frontmatter shape) must be reported
    rather than silently coerced. Closes reviewer 0.11.0 finding
    'non-dict YAML root not asserted' (verification axis)."""
    p = _write_agent(tmp_path, "list-root-agent", "---\n- item1\n- item2\n---\n")
    assert vh.validate_agent(p) > 0
    captured = capsys.readouterr()
    assert "must be a mapping" in captured.out


def test_skill_non_dict_yaml_root_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Same parity for skill validator."""
    skill_dir = tmp_path / "list-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n- not-a-mapping\n---\nbody\n", encoding="utf-8"
    )
    assert vh.validate_skill(skill_dir) > 0
    captured = capsys.readouterr()
    assert "must be a mapping" in captured.out


# ---------- CLI dispatch ----------


def test_main_unknown_command_returns_2(tmp_path: Path) -> None:
    assert vh.main(["_validate_helpers.py", "nonsense", str(tmp_path)]) == 2


def test_main_insufficient_args_returns_2() -> None:
    assert vh.main(["_validate_helpers.py", "opencode_json"]) == 2
