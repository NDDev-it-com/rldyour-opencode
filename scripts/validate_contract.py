#!/usr/bin/env python3
"""Validate references/rldyour-contract.json against the OpenCode adapter.

The contract is the canonical cross-tool vocabulary: domains, lifecycle
flows, review agents, adapter-only surfaces, and hook lifecycle IDs. This
validator proves the OpenCode mapping points at real local files and real
plugin hook subscriptions.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "references" / "rldyour-contract.json"
OPENCODE_CONFIG = REPO_ROOT / "opencode.json"
SKILLS_INDEX = REPO_ROOT / ".opencode" / "skills" / "index.json"
COMMANDS_INDEX = REPO_ROOT / ".opencode" / "commands" / "index.json"
PLUGINS_INDEX = REPO_ROOT / ".opencode" / "plugins" / "index.json"
AGENTS_DIR = REPO_ROOT / ".opencode" / "agents"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"{path.relative_to(REPO_ROOT)} missing") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path.relative_to(REPO_ROOT)} invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path.relative_to(REPO_ROOT)} must be a JSON object")
    return data


def _values(mapping: object) -> set[str]:
    if not isinstance(mapping, dict):
        return set()
    return {str(value) for value in mapping.values()}


def validate() -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    opencode_config = _load_json(OPENCODE_CONFIG)
    skills_index = _load_json(SKILLS_INDEX)
    commands_index = _load_json(COMMANDS_INDEX)
    plugins_index = _load_json(PLUGINS_INDEX)

    problems: list[str] = []
    warnings: list[str] = []

    domains = set(contract.get("domains") or [])
    if not domains:
        problems.append("contract.domains must be non-empty")

    skill_names = {entry["name"] for entry in skills_index.get("skills", [])}
    command_names = {entry["name"] for entry in commands_index.get("commands", [])}
    agent_names = {path.stem for path in AGENTS_DIR.glob("*.md")}
    plugin_by_name = {entry["name"]: entry for entry in plugins_index.get("plugins", [])}

    security = contract.get("security")
    if not isinstance(security, dict):
        problems.append("contract.security must be an object")
    else:
        if security.get("full_auto_standard") is not True:
            problems.append("contract.security.full_auto_standard must be true")
        aliases = set(security.get("dangerously_skip_permissions_aliases") or [])
        for alias in ("yolo", "full-auto", "dangerously-skip-permissions"):
            if alias not in aliases:
                problems.append(f"contract.security.dangerously_skip_permissions_aliases missing {alias!r}")
        if security.get("safe_override") != "local-operator-config-only":
            problems.append("contract.security.safe_override must be local-operator-config-only")
        if security.get("forbidden_enforcement_hook") != "permission.ask":
            problems.append("contract.security.forbidden_enforcement_hook must be permission.ask")

        expected_permissions = security.get("standard_permissions")
        if not isinstance(expected_permissions, dict):
            problems.append("contract.security.standard_permissions must be an object")
        else:
            actual_top = opencode_config.get("permission") or {}
            actual_build = ((opencode_config.get("agent") or {}).get("build") or {}).get("permission") or {}
            actual_plan = ((opencode_config.get("agent") or {}).get("plan") or {}).get("permission") or {}
            for scope_name, actual_permissions in (
                ("top_level", actual_top),
                ("build", actual_build),
                ("plan", actual_plan),
            ):
                expected_scope = expected_permissions.get(scope_name)
                if not isinstance(expected_scope, dict):
                    problems.append(
                        f"contract.security.standard_permissions.{scope_name} must be an object"
                    )
                    continue
                for permission, expected_value in expected_scope.items():
                    actual_value = actual_permissions.get(permission)
                    if actual_value != expected_value:
                        problems.append(
                            f"opencode.json {scope_name} permission {permission!r} is {actual_value!r}; "
                            f"expected {expected_value!r}"
                        )

    contract_skills = _values(contract.get("skills"))
    missing_skills = sorted(contract_skills - skill_names)
    extra_skills = sorted(skill_names - contract_skills)
    for name in missing_skills:
        problems.append(f"contract skill mapping points to missing skill {name!r}")
    for name in extra_skills:
        warnings.append(f"skill {name!r} exists but is not mapped to a canonical skill ID")

    contract_commands = _values(contract.get("commands")) | _values(contract.get("adapter_only_commands"))
    missing_commands = sorted(contract_commands - command_names)
    extra_commands = sorted(command_names - contract_commands)
    for name in missing_commands:
        problems.append(f"contract command mapping points to missing command {name!r}")
    for name in extra_commands:
        problems.append(f"command {name!r} exists but is not mapped or marked adapter-only")

    contract_agents = _values(contract.get("agents")) | _values(contract.get("adapter_only_agents"))
    missing_agents = sorted(contract_agents - agent_names)
    extra_agents = sorted(agent_names - contract_agents)
    for name in missing_agents:
        problems.append(f"contract agent mapping points to missing agent {name!r}")
    for name in extra_agents:
        problems.append(f"agent {name!r} exists but is not mapped or marked adapter-only")

    for canonical_id, item in (contract.get("hook_lifecycle") or {}).items():
        if not isinstance(item, dict):
            problems.append(f"hook_lifecycle.{canonical_id}: value must be an object")
            continue
        plugin_name = item.get("plugin")
        hook = item.get("hook")
        if plugin_name not in plugin_by_name:
            problems.append(f"hook_lifecycle.{canonical_id}: plugin {plugin_name!r} missing from index")
            continue
        hooks = set(plugin_by_name[plugin_name].get("hooks") or [])
        if hook not in hooks:
            problems.append(
                f"hook_lifecycle.{canonical_id}: plugin {plugin_name!r} does not subscribe to hook {hook!r}"
            )
        if hook == "permission.ask":
            problems.append(f"hook_lifecycle.{canonical_id}: permission.ask is forbidden as a lifecycle hook")

    contract_domain_values = set()
    for section in ("skills", "commands", "adapter_only_commands", "agents", "adapter_only_agents", "hook_lifecycle"):
        for key in (contract.get(section) or {}).keys():
            if "." in key:
                contract_domain_values.add(key.split(".", 1)[0])
    unknown_domains = sorted(contract_domain_values - domains - {"agent", "prompt", "session", "shell", "tool", "command", "permission"})
    for domain in unknown_domains:
        problems.append(f"canonical IDs reference undeclared domain {domain!r}")

    return {
        "ok": not problems,
        "problems": problems,
        "warnings": warnings,
        "counts": {
            "skills": len(skill_names),
            "commands": len(command_names),
            "agents": len(agent_names),
            "plugins": len(plugin_by_name),
            "hook_lifecycle": len(contract.get("hook_lifecycle") or {}),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the rldyour OpenCode adapter contract.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON result envelope.")
    args = parser.parse_args(argv)

    try:
        result = validate()
    except RuntimeError as exc:
        print(f"[ERR] {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for warning in result["warnings"]:
            print(f"[WARN] {warning}", file=sys.stderr)
        if result["ok"]:
            counts = result["counts"]
            print(
                "[OK] rldyour contract valid: "
                f"skills={counts['skills']}, commands={counts['commands']}, "
                f"agents={counts['agents']}, plugins={counts['plugins']}, "
                f"hook_lifecycle={counts['hook_lifecycle']}"
            )
        else:
            print(f"[FAIL] rldyour contract drift: {len(result['problems'])} problem(s)", file=sys.stderr)
            for problem in result["problems"]:
                print(f"  - {problem}", file=sys.stderr)

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
