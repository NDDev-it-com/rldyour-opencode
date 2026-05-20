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
    assert counts["skills"] == 32
    assert counts["commands"] == 10
    assert counts["agents"] == 9
    assert counts["plugins"] == 10
    assert counts["hook_lifecycle"] >= 10


def test_contract_has_explicit_opencode_only_surfaces() -> None:
    contract = json.loads(validate_contract.CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["adapter_only_commands"]["flow.sync.manual"] == "ry-sync"
    assert contract["adapter_only_agents"]["agent.adapter.opencode-customizer"] == "customize-opencode"


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
    monkeypatch.setattr(validate_contract, "SKILLS_INDEX", tmp_path / ".opencode" / "skills" / "index.json")
    monkeypatch.setattr(validate_contract, "COMMANDS_INDEX", tmp_path / ".opencode" / "commands" / "index.json")
    monkeypatch.setattr(validate_contract, "PLUGINS_INDEX", tmp_path / ".opencode" / "plugins" / "index.json")
    monkeypatch.setattr(validate_contract, "AGENTS_DIR", tmp_path / ".opencode" / "agents")

    result = validate_contract.validate()
    assert not result["ok"]
    assert any("missing-skill" in problem for problem in result["problems"])
