#!/usr/bin/env python3
"""Static check for GitHub Actions script injection patterns.

The GitHub Actions hardening guide (https://docs.github.com/en/actions/
security-guides/security-hardening-for-github-actions) warns that
`${{ <expr> }}` substitution placed directly inside a `run:` shell block
is evaluated by the GitHub Actions runner BEFORE shell quoting, so any
attacker-controlled token reaches the bash parser unescaped. A payload
like `v0.12.3'; cat /etc/passwd; echo '` would execute commands inside
the runner.

This script scans every workflow under `.github/workflows/*.yml` for the
canonical risky shapes inside `run:` bodies:

  - `${{ inputs.<name> }}`        - workflow_dispatch input
  - `${{ github.event.<path> }}`  - PR/issue title, head_ref, comment body

The safe pattern is to map the expression through `env:` first and then
reference the env var inside the shell. The reviewer wave 2026-05-18
security F-3 closed two such vectors in `.github/workflows/release.yml`.

Exit codes:
    0 - no vectors found
    1 - one or more vectors found
    2 - operational error (missing dir, malformed YAML, missing PyYAML)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = PROJECT_ROOT / ".github" / "workflows"

# Match `${{ inputs.X }}` or `${{ github.event.X }}` substitutions. Whitespace
# tolerance covers `${{  inputs.tag  }}` style formatting variants.
INJECTION_RE = re.compile(
    r"\$\{\{\s*(inputs\.[\w.\-]+|github\.event\.[\w.\-]+)\s*\}\}"
)


def _iter_run_blocks(data: dict[str, Any]) -> list[tuple[str, int, str, str]]:
    """Return (job_id, step_idx, step_name, run_body) for every `run:` step."""
    out: list[tuple[str, int, str, str]] = []
    jobs = data.get("jobs") or {}
    if not isinstance(jobs, dict):
        return out
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps") or []
        if not isinstance(steps, list):
            continue
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            run = step.get("run")
            if not isinstance(run, str):
                continue
            name = str(step.get("name") or f"step-{idx}")
            out.append((str(job_id), idx, name, run))
    return out


def scan_workflow(path: Path) -> list[str]:
    """Return human-readable finding lines for the workflow file."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        print(
            "[ERR] PyYAML is required for check_workflow_injection.py; "
            "install via `uvx --from pyyaml ...` or `pip install pyyaml==6.0.3`.",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:  # type: ignore[attr-defined]
        return [f"{path.name}: malformed YAML: {exc}"]
    if not isinstance(data, dict):
        return []
    findings: list[str] = []
    for job_id, step_idx, step_name, run in _iter_run_blocks(data):
        for match in INJECTION_RE.findall(run):
            findings.append(
                f"{path.name}::{job_id}#{step_idx} ({step_name}): "
                f"unsafe `${{{{ {match} }}}}` in `run:` block"
            )
    return findings


def main() -> int:
    if not WORKFLOWS_DIR.is_dir():
        print(f"[ERR] workflows dir missing: {WORKFLOWS_DIR}", file=sys.stderr)
        return 2
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml"))
    if not workflow_files:
        print(f"[INFO] no .yml workflows under {WORKFLOWS_DIR}")
        return 0
    all_findings: list[str] = []
    for wf in workflow_files:
        all_findings.extend(scan_workflow(wf))
    if all_findings:
        for line in all_findings:
            print(f"[ERR] script injection: {line}")
        print(
            f"[FAIL] {len(all_findings)} script injection vector(s) across "
            f"{len(workflow_files)} workflows. Map the expression through "
            f"`env:` before referencing in `run:`.",
            file=sys.stderr,
        )
        return 1
    print(
        f"[OK] no script injection vectors in {len(workflow_files)} workflow "
        f"file(s) under {WORKFLOWS_DIR.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
