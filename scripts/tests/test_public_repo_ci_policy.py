"""Regression tests for the public-repository CI/CD policy.

The policy intentionally lives in an OpenCode instruction file instead of
overloading `opencode.json.share`, which controls session sharing only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENCODE_JSON = REPO_ROOT / "opencode.json"
POLICY = REPO_ROOT / "references" / "public-repo-ci-policy.md"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
COMMANDS = (
    REPO_ROOT / ".opencode" / "commands" / "ry-start.md",
    REPO_ROOT / ".opencode" / "commands" / "ry-sync.md",
    REPO_ROOT / ".opencode" / "commands" / "ry-deploy.md",
)


def _workflow_triggers(data: dict[str, Any]) -> set[str]:
    # PyYAML parses `on:` as boolean True under YAML 1.1 rules.
    raw = data.get(True, data.get("on"))
    if isinstance(raw, dict):
        return {str(key) for key in raw.keys()}
    if isinstance(raw, list):
        return {str(item) for item in raw}
    if isinstance(raw, str):
        return {raw}
    return set()


def test_public_ci_policy_is_loaded_by_opencode_instructions() -> None:
    cfg = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    assert cfg["share"] == "manual"
    assert cfg["instructions"] == [
        "AGENTS.md",
        "references/public-repo-ci-policy.md",
    ]


def test_public_ci_policy_distinguishes_ci_from_session_sharing() -> None:
    text = POLICY.read_text(encoding="utf-8")
    assert "Public repositories must use automatic CI/CD by default." in text
    assert 'share: "manual"' in text
    assert "session sharing, not CI/CD" in text


def test_flow_commands_reference_public_ci_policy() -> None:
    expected = "references/public-repo-ci-policy.md"
    for command in COMMANDS:
        text = command.read_text(encoding="utf-8")
        assert "Public repository exception" in text, command
        assert expected in text, command


def test_public_repo_workflows_have_non_manual_triggers() -> None:
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml"))
    assert workflow_files
    manual_only: list[str] = []
    for workflow in workflow_files:
        data = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
        triggers = _workflow_triggers(data)
        if triggers == {"workflow_dispatch"}:
            manual_only.append(workflow.name)
    assert not manual_only, (
        "public repository workflows must not be manual-only by default: "
        f"{manual_only}"
    )
