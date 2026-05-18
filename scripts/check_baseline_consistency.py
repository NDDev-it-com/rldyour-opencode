#!/usr/bin/env python3
"""Verify that every place in the repo that names an OpenCode/runtime version
agrees with `references/opencode-baseline.json`.

The 2026-05-17 external audit found a drift where `.opencode/package.json`
and `.opencode/bun.lock` pinned `@opencode-ai/plugin@1.15.3` while README,
AGENTS.md, CHANGELOG, and references claimed `1.15.4`. This validator is
the single gate that makes "the marketplace targets one consistent OpenCode
baseline" a fact, not a hope. Run it from CI before any release.

Exit codes:
- 0: every checked location agrees with the baseline.
- 1: at least one location drifts; per-drift message printed to stderr.
- 2: operational error (missing baseline file, malformed JSON, etc.).

The matcher is intentionally conservative: it only flags exact pinned
versions, not historical mentions or version-spec ranges. The intent is
to keep release coordinates aligned, not to police every changelog line.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "references" / "opencode-baseline.json"


def _load_baseline() -> dict[str, Any]:
    if not BASELINE_PATH.exists():
        print(f"[ERR] baseline missing: {BASELINE_PATH}", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERR] baseline parse: {exc}", file=sys.stderr)
        sys.exit(2)
    baseline = data.get("baseline")
    if not isinstance(baseline, dict):
        print("[ERR] baseline.baseline must be an object", file=sys.stderr)
        sys.exit(2)
    return baseline


def _check_package_json(plugin_version: str) -> list[str]:
    """`.opencode/package.json` must pin the plugin SDK at the baseline."""
    path = REPO_ROOT / ".opencode" / "package.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read {path}: {exc}"]
    actual = data.get("dependencies", {}).get("@opencode-ai/plugin", "")
    if actual != plugin_version:
        return [
            f".opencode/package.json @opencode-ai/plugin = {actual!r}, "
            f"baseline expects {plugin_version!r}"
        ]
    return []


def _check_bun_lock(plugin_version: str, sdk_version: str) -> list[str]:
    """`.opencode/bun.lock` must resolve both the plugin and SDK at the baseline.

    Quality-review finding: a single `re.search` would only inspect the
    first match. Bun lockfiles can list the same package multiple times
    (workspace root + peer-dependencies + transitive references), so use
    `findall` and validate every occurrence so a drift hidden later in
    the file cannot pass.
    """
    path = REPO_ROOT / ".opencode" / "bun.lock"
    if not path.exists():
        return [f"bun.lock missing at {path} — run `cd .opencode && bun install`"]
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []
    plugin_re = re.compile(r'"@opencode-ai/plugin":\s*\["@opencode-ai/plugin@([0-9][^"]+)"')
    sdk_re = re.compile(r'"@opencode-ai/sdk":\s*\["@opencode-ai/sdk@([0-9][^"]+)"')
    plugin_matches = plugin_re.findall(text)
    sdk_matches = sdk_re.findall(text)
    if not plugin_matches:
        problems.append(
            f"bun.lock @opencode-ai/plugin not found; baseline expects {plugin_version!r}"
        )
    for actual in plugin_matches:
        if actual != plugin_version:
            problems.append(
                f"bun.lock @opencode-ai/plugin resolved to {actual!r}, "
                f"baseline expects {plugin_version!r}"
            )
    if not sdk_matches:
        problems.append(
            f"bun.lock @opencode-ai/sdk not found; baseline expects {sdk_version!r}"
        )
    for actual in sdk_matches:
        if actual != sdk_version:
            problems.append(
                f"bun.lock @opencode-ai/sdk resolved to {actual!r}, "
                f"baseline expects {sdk_version!r}"
            )
    return problems


def _check_opencode_runtime_workflow(cli_version: str, bun_version: str) -> list[str]:
    """Pinned install lines in the runtime workflow."""
    path = REPO_ROOT / ".github" / "workflows" / "opencode-runtime.yml"
    if not path.exists():
        return [f"workflow missing at {path}"]
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []
    cli_pattern = re.compile(r'opencode-ai@([0-9][^\s]+)')
    cli_matches = cli_pattern.findall(text)
    if not cli_matches:
        problems.append("opencode-runtime.yml does not pin opencode-ai@<version>")
    for actual in cli_matches:
        if actual != cli_version:
            problems.append(
                f"opencode-runtime.yml pins opencode-ai@{actual!r}, "
                f"baseline expects {cli_version!r}"
            )
    bun_pattern = re.compile(r'bun-version:\s*"([0-9][^"]+)"')
    bun_matches = bun_pattern.findall(text)
    for actual in bun_matches:
        if actual != bun_version:
            problems.append(
                f"opencode-runtime.yml bun-version = {actual!r}, "
                f"baseline expects {bun_version!r}"
            )
    return problems


def _check_workflow_bun_pins(bun_version: str) -> list[str]:
    """Every workflow that installs Bun must use the baseline version."""
    problems: list[str] = []
    workflows = REPO_ROOT / ".github" / "workflows"
    bun_pattern = re.compile(r'bun-version:\s*"([0-9][^"]+)"')
    for yml in sorted(workflows.glob("*.yml")):
        for actual in bun_pattern.findall(yml.read_text(encoding="utf-8")):
            if actual != bun_version:
                problems.append(
                    f"{yml.name} bun-version = {actual!r}, baseline expects {bun_version!r}"
                )
    return problems


def _check_workflow_python_pins(
    pytest_ver: str,
    pyyaml_ver: str,
    jsonschema_ver: str,
    ruff_ver: str,
    referencing_ver: str | None = None,
) -> list[str]:
    """Every workflow that installs pytest/PyYAML/jsonschema/ruff/referencing must use the baseline pins.

    Quality-review F-1 + integration-review F-2: the original
    implementation anchored the pin extractor on the literal `pip
    install` prefix and `re.findall` only returned ONE match per line —
    every additional pinned package on the same `pip install` command
    was silently ignored. Workflows here typically install three packages
    in one line:

        python3 -m pip install --upgrade pip "pytest==9.0.3" "PyYAML==6.0.3" "jsonschema==4.26.0"

    The fix walks each `pip install` line, then runs a second pass over
    that line to extract every `"pkg==ver"` token so drift on the
    second/third pin can no longer slip past the gate. The expected map
    also picked up `ruff` (was previously `None` = disabled) and the new
    `referencing` pin so all dependencies declared in the baseline are
    enforced symmetrically.
    """
    problems: list[str] = []
    workflows = REPO_ROOT / ".github" / "workflows"
    expected: dict[str, str | None] = {
        "pytest": pytest_ver,
        "PyYAML": pyyaml_ver,
        "jsonschema": jsonschema_ver,
        "ruff": ruff_ver,
        "referencing": referencing_ver,
    }
    line_with_pip_install = re.compile(r"pip install[^\n]*")
    pin_re = re.compile(r'"([A-Za-z0-9_-]+)==([0-9][^"]+)"')
    for yml in sorted(workflows.glob("*.yml")):
        text = yml.read_text(encoding="utf-8")
        for line in line_with_pip_install.findall(text):
            for pkg, ver in pin_re.findall(line):
                target = expected.get(pkg)
                if target is not None and ver != target:
                    problems.append(
                        f"{yml.name} {pkg}=={ver!r}, baseline expects {target!r}"
                    )
    return problems


def _check_schema_vendored(schema_version: str, vendored_path: str, external_refs: list[str]) -> list[str]:
    problems: list[str] = []
    expected_path = REPO_ROOT / vendored_path
    if not expected_path.exists():
        problems.append(f"vendored schema missing at {vendored_path}")
    for ref_path in external_refs:
        ref_file = REPO_ROOT / ref_path
        if not ref_file.exists():
            problems.append(f"external-ref vendored file missing at {ref_path}")
    return problems


def _check_changelog_release_anchor(plugin_version: str) -> list[str]:
    """The latest CHANGELOG release entry should mention the baseline plugin version."""
    path = REPO_ROOT / "CHANGELOG.md"
    if not path.exists():
        return [f"CHANGELOG.md missing at {path}"]
    text = path.read_text(encoding="utf-8")
    # Find the first concrete SemVer release block, skipping `[Unreleased]`.
    first_release = re.search(
        r"^## \[\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?\][^\n]*$",
        text,
        flags=re.MULTILINE,
    )
    if not first_release:
        return ["CHANGELOG.md has no [X.Y.Z] release header"]
    start = first_release.start()
    next_release = re.search(r"^## \[[^\]]+\]", text[first_release.end():], flags=re.MULTILINE)
    end = first_release.end() + next_release.start() if next_release else len(text)
    block = text[start:end]
    if plugin_version not in block:
        return [
            f"latest CHANGELOG release block does not mention plugin version {plugin_version!r}; "
            f"this is non-fatal but suggests doc drift"
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify pinned versions across the repo agree with the baseline.")
    parser.add_argument("--no-changelog", action="store_true", help="Skip the soft CHANGELOG mention check.")
    parser.add_argument("--json", action="store_true", help="Emit a structured JSON envelope on stdout.")
    args = parser.parse_args(argv)

    baseline = _load_baseline()
    plugin_version = baseline["plugin_sdk"]["version"]
    sdk_version = baseline["sdk"]["version"]
    cli_version = baseline["opencode_cli"]["version"]
    bun_version = baseline["bun_runtime"]["version"]
    pytest_ver = baseline["test_dependencies"]["pytest"]
    pyyaml_ver = baseline["test_dependencies"]["pyyaml"]
    jsonschema_ver = baseline["test_dependencies"]["jsonschema"]
    ruff_ver = baseline["test_dependencies"].get("ruff")
    referencing_ver = baseline["test_dependencies"].get("referencing")
    schema_version = baseline["config_schema"]["version"]
    vendored_path = baseline["config_schema"]["vendored_at"]
    external_refs = baseline["config_schema"]["external_refs_vendored_at"]
    _ = schema_version  # surfaced in the JSON envelope baseline echo; suppresses unused warning

    hard_problems: list[str] = []
    hard_problems.extend(_check_package_json(plugin_version))
    hard_problems.extend(_check_bun_lock(plugin_version, sdk_version))
    hard_problems.extend(_check_opencode_runtime_workflow(cli_version, bun_version))
    hard_problems.extend(_check_workflow_bun_pins(bun_version))
    hard_problems.extend(
        _check_workflow_python_pins(
            pytest_ver, pyyaml_ver, jsonschema_ver, ruff_ver or "", referencing_ver
        )
    )
    hard_problems.extend(_check_schema_vendored(schema_version, vendored_path, external_refs))

    soft_warnings: list[str] = []
    if not args.no_changelog:
        soft_warnings.extend(_check_changelog_release_anchor(plugin_version))

    if args.json:
        envelope = {
            "baseline": baseline,
            "problems": hard_problems,
            "warnings": soft_warnings,
            "ok": not hard_problems,
        }
        print(json.dumps(envelope, indent=2))
        return 0 if not hard_problems else 1

    if hard_problems:
        print(f"[FAIL] baseline drift: {len(hard_problems)} hard problem(s):", file=sys.stderr)
        for problem in hard_problems:
            print(f"  - {problem}", file=sys.stderr)
        if soft_warnings:
            print(f"[WARN] {len(soft_warnings)} soft warning(s):", file=sys.stderr)
            for warning in soft_warnings:
                print(f"  - {warning}", file=sys.stderr)
        return 1
    for warning in soft_warnings:
        print(f"[WARN] {warning}", file=sys.stderr)
    # Reviewer wave 2026-05-18 integration F-8 closure: include every pin
    # the validator actually checks in the OK summary so operators see the
    # full per-key freshness state at a glance, not just the seven pins the
    # original line printed.
    print(
        f"[OK] baseline consistent: opencode-cli={cli_version}, "
        f"plugin={plugin_version}, sdk={sdk_version}, bun={bun_version}, "
        f"pytest={pytest_ver}, pyyaml={pyyaml_ver}, jsonschema={jsonschema_ver}, "
        f"referencing={referencing_ver or 'n/a'}, ruff={ruff_ver or 'n/a'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
