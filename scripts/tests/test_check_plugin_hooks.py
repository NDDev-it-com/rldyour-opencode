"""Tests for scripts/check_plugin_hooks.py."""
from __future__ import annotations

from pathlib import Path

import check_plugin_hooks as hooks


def test_live_plugin_hook_contract_is_clean() -> None:
    result = hooks.validate_all()
    assert result["ok"], result


def test_permission_ask_is_forbidden(tmp_path: Path) -> None:
    plugin = tmp_path / "bad.ts"
    plugin.write_text(
        'export const Bad = async () => ({\n  "permission.ask": async () => {},\n})\n',
        encoding="utf-8",
    )
    result = hooks.validate_plugin(plugin)
    assert result["problems"]
    assert "forbidden hook" in result["problems"][0]


def test_permission_asked_is_event_type_not_top_level_hook(tmp_path: Path) -> None:
    plugin = tmp_path / "bad-event.ts"
    plugin.write_text(
        'export const Bad = async () => ({\n  "permission.asked": async () => {},\n})\n',
        encoding="utf-8",
    )
    result = hooks.validate_plugin(plugin)
    assert result["problems"]
    assert "event.type value" in result["problems"][0]


def test_event_handler_can_compare_permission_events(tmp_path: Path) -> None:
    plugin = tmp_path / "observer.ts"
    plugin.write_text(
        'export const Observer = async () => ({\n'
        "  event: async ({ event }) => {\n"
        '    if (event.type === "permission.asked") return\n'
        "  },\n"
        "})\n",
        encoding="utf-8",
    )
    result = hooks.validate_plugin(plugin)
    assert result["problems"] == []
    assert result["hooks"] == ["event"]
