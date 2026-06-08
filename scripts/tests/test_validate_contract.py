"""Tests for scripts/validate_contract.py."""
from __future__ import annotations

import json
from pathlib import Path

import validate_contract


def test_live_contract_is_valid() -> None:
    result = validate_contract.validate()
    assert result["ok"], result


def test_contract_counts_cover_runtime_surfaces() -> None:
    result = validate_contract.validate()
    counts = result["counts"]
    assert counts["skills"] == 38
    assert counts["commands"] == 11
    assert counts["agents"] == 9
    assert counts["plugins"] == 10
    assert counts["hook_lifecycle"] >= 10


def test_contract_has_manual_sync_as_canonical_flow() -> None:
    contract = json.loads(validate_contract.CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["commands"]["flow.sync.manual"] == "ry-sync"
    assert contract["commands"]["flow.repair"] == "ry-repair"
    assert "flow.sync.manual" not in contract["adapter_only_commands"]
    assert contract["adapter_only_agents"]["agent.adapter.opencode-customizer"] == "customize-opencode"


def test_contract_requires_owner_full_auto_standard_permissions() -> None:
    contract = json.loads(validate_contract.CONTRACT_PATH.read_text(encoding="utf-8"))
    security = contract["security"]
    assert security["full_auto_standard"] is True
    assert set(security["dangerously_skip_permissions_aliases"]) == {
        "yolo",
        "full-auto",
        "dangerously-skip-permissions",
    }
    assert security["safe_override"] == "local-operator-config-only"
    assert security["forbidden_enforcement_hook"] == "permission.ask"
    assert security["standard_permissions"]["top_level"] == {
        "read": "allow",
        "edit": "allow",
        "glob": "allow",
        "grep": "allow",
        "list": "allow",
        "bash": "allow",
        "task": "allow",
        "external_directory": "allow",
        "todowrite": "allow",
        "question": "allow",
        "webfetch": "allow",
        "websearch": "allow",
        "repo_clone": "allow",
        "repo_overview": "allow",
        "lsp": "allow",
        "doom_loop": "allow",
        "skill": "allow",
    }
    assert security["standard_permissions"]["build"] == security["standard_permissions"]["top_level"]
    assert security["standard_permissions"]["plan"] == security["standard_permissions"]["top_level"]
    assert security["read_policy"]["owner_full_auto_read"] == "allow"
    assert security["read_policy"]["source"] == "docs/decisions/010-owner-full-auto-standard-mode.md"
    assert "ry-env-protection" in security["read_policy"]["guardrail"]
    assert security["no_prompt_policy"]["external_directory"] == "allow"
    assert security["no_prompt_policy"]["doom_loop"] == "allow"


def test_permission_ask_not_in_lifecycle_contract() -> None:
    contract = json.loads(validate_contract.CONTRACT_PATH.read_text(encoding="utf-8"))
    hooks = [item["hook"] for item in contract["hook_lifecycle"].values()]
    assert "permission.ask" not in hooks


def test_validator_reports_missing_skill(monkeypatch, tmp_path: Path) -> None:
    contract = json.loads(validate_contract.CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["skills"]["flow.start"] = "missing-skill"
    (tmp_path / "references").mkdir()
    (tmp_path / ".opencode" / "skills").mkdir(parents=True)
    (tmp_path / ".opencode" / "commands").mkdir(parents=True)
    (tmp_path / ".opencode" / "plugins").mkdir(parents=True)
    (tmp_path / ".opencode" / "agents").mkdir(parents=True)
    (tmp_path / "references" / "rldyour-contract.json").write_text(json.dumps(contract), encoding="utf-8")
    (tmp_path / ".opencode" / "skills" / "index.json").write_text(
        json.dumps({"skills": [{"name": "ry-start"}]}), encoding="utf-8"
    )
    (tmp_path / ".opencode" / "commands" / "index.json").write_text(
        json.dumps({"commands": []}), encoding="utf-8"
    )
    (tmp_path / ".opencode" / "plugins" / "index.json").write_text(
        json.dumps({"plugins": []}), encoding="utf-8"
    )
    monkeypatch.setattr(validate_contract, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(validate_contract, "CONTRACT_PATH", tmp_path / "references" / "rldyour-contract.json")
    monkeypatch.setattr(validate_contract, "OPENCODE_CONFIG", tmp_path / "opencode.json")
    monkeypatch.setattr(validate_contract, "SKILLS_INDEX", tmp_path / ".opencode" / "skills" / "index.json")
    monkeypatch.setattr(validate_contract, "COMMANDS_INDEX", tmp_path / ".opencode" / "commands" / "index.json")
    monkeypatch.setattr(validate_contract, "PLUGINS_INDEX", tmp_path / ".opencode" / "plugins" / "index.json")
    monkeypatch.setattr(validate_contract, "AGENTS_DIR", tmp_path / ".opencode" / "agents")
    (tmp_path / "opencode.json").write_text(
        json.dumps(
            {
                "permission": {"edit": "allow", "bash": "allow"},
                "agent": {
                    "build": {"permission": {"edit": "allow", "bash": "allow"}},
                    "plan": {"permission": {"edit": "allow", "bash": "allow"}},
                },
            }
        ),
        encoding="utf-8",
    )

    result = validate_contract.validate()
    assert not result["ok"]
    assert any("missing-skill" in problem for problem in result["problems"])
