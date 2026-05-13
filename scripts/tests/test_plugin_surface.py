"""Plugin surface integrity tests.

Verify that the 8 plugins listed in AGENTS.md actually exist on disk, that
ry-tool-hints' HINTS keys reference real MCP servers from opencode.json,
and that ry-tools' registered tool IDs match what AGENTS.md and CHANGELOG
claim. Catches future drift between plugin code, the manifest, and
human-facing docs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLUGINS_DIR = PROJECT_ROOT / ".opencode" / "plugins"
OPENCODE_JSON = PROJECT_ROOT / "opencode.json"
AGENTS_MD = PROJECT_ROOT / "AGENTS.md"

EXPECTED_PLUGINS = {
    "ry-bootstrap.ts",
    "ry-env-protection.ts",
    "ry-shell-strategy.ts",
    "ry-sync-reminder.ts",
    "ry-flow-hooks.ts",
    "ry-tools.ts",
    "ry-command-audit.ts",
    "ry-tool-hints.ts",
}

EXPECTED_RY_TOOL_IDS = {
    "rldyour_validate_config",
    "rldyour_check_deps",
    "rldyour_lsp_health",
    "rldyour_git_audit",
    "rldyour_fullrepo_status",
}


def test_all_expected_plugins_exist() -> None:
    actual = {p.name for p in PLUGINS_DIR.glob("*.ts")}
    assert actual == EXPECTED_PLUGINS, (
        f"plugin set drifted — extra={actual - EXPECTED_PLUGINS}, missing={EXPECTED_PLUGINS - actual}"
    )


def test_plugin_count_matches_agents_md() -> None:
    text = AGENTS_MD.read_text(encoding="utf-8-sig")
    match = re.search(r"rldyour plugins \((\d+)\)", text)
    assert match, "AGENTS.md must list 'rldyour plugins (N)'"
    declared = int(match.group(1))
    actual = len(list(PLUGINS_DIR.glob("*.ts")))
    assert declared == actual, f"AGENTS.md says {declared} plugins but {actual} exist on disk"


def test_ry_tools_registers_expected_ids() -> None:
    src = (PLUGINS_DIR / "ry-tools.ts").read_text(encoding="utf-8")
    found = set(re.findall(r"^\s*(rldyour_[A-Za-z0-9_]+):\s*tool\(", src, re.MULTILINE))
    assert found == EXPECTED_RY_TOOL_IDS, (
        f"ry-tools.ts ID drift — extra={found - EXPECTED_RY_TOOL_IDS}, "
        f"missing={EXPECTED_RY_TOOL_IDS - found}"
    )


def test_ry_tool_hints_references_real_mcp_servers() -> None:
    """Every `mcp__<server>__<tool>` key in HINTS must use a server that
    exists in opencode.json.mcp. Catches drift when an MCP server is
    renamed or removed."""
    cfg = json.loads(OPENCODE_JSON.read_text(encoding="utf-8-sig"))
    mcp_servers = set((cfg.get("mcp") or {}).keys())

    hints_src = (PLUGINS_DIR / "ry-tool-hints.ts").read_text(encoding="utf-8")
    keys = re.findall(r'"mcp__([a-zA-Z0-9_\-]+)__[^"]+"', hints_src)

    unknown = {k for k in keys if k not in mcp_servers}
    assert not unknown, (
        f"ry-tool-hints.ts references MCP server(s) not in opencode.json: {unknown}"
    )


def test_ry_tool_hints_no_legacy_aliases() -> None:
    """Defensive: catch the previous bug where the Context7 hint used a
    non-existent tool name. Add explicit blacklist as bugs are fixed so
    they cannot regress."""
    LEGACY_BANNED = {
        "mcp__context7__get-library-docs",  # never existed; real names are query-docs / resolve-library-id
    }
    hints_src = (PLUGINS_DIR / "ry-tool-hints.ts").read_text(encoding="utf-8")
    for banned in LEGACY_BANNED:
        assert banned not in hints_src, f"ry-tool-hints.ts contains legacy alias {banned!r}"


def test_no_dead_project_path_cast_in_plugins() -> None:
    """Defensive: catches re-introduction of the `project as { path? }`
    cast that was dead code (Project type has no `path` field in v1.14.48).
    Plugins should destructure `directory` directly from PluginInput.
    """
    for ts in PLUGINS_DIR.glob("*.ts"):
        src = ts.read_text(encoding="utf-8")
        assert "as { path?: string }" not in src, (
            f"{ts.name} re-introduced the dead `project as {{ path? }}` cast"
        )
