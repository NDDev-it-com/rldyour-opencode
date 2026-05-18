#!/usr/bin/env bash
# Print the GitHub check contexts produced by each workflow under
# `.github/workflows/`. The output is the canonical name used in
# `gh api repos/<owner>/<repo>/branches/main/protection
# -F required_status_checks.contexts[]=...` — i.e. workflow `name:`
# plus job `name:` (or job key when `name:` is absent), with matrix
# expansions enumerated.
#
# Audit P0-5: branch-protection docs must match the actual check
# contexts GitHub emits. This script prints the truth from the
# workflow source files so docs/github/branch-protection.md can be
# generated and audited mechanically.
#
# Output format:
#   <workflow-name> / <job-display-name>
# One line per (workflow × job × matrix-cell). Matrix axes are
# enumerated alphabetically; matrix-aware job names use the standard
# GitHub convention `<job-name> (<matrix-value-1>, <matrix-value-2>)`.
#
# Usage:
#   bash scripts/print_required_check_contexts.sh           # human text
#   bash scripts/print_required_check_contexts.sh --json    # JSON envelope
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKFLOWS_DIR="${PROJECT_ROOT}/.github/workflows"

FORMAT="text"
if [[ "${1:-}" == "--json" ]]; then
  FORMAT="json"
fi

if [[ ! -d "${WORKFLOWS_DIR}" ]]; then
  echo "[ERR] workflows dir not found: ${WORKFLOWS_DIR}" >&2
  exit 2
fi

python3 - "$WORKFLOWS_DIR" "$FORMAT" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    # Quality-review F-4 / Architecture F-1: report a clean operator
    # message instead of a Python traceback. Same exit code as the rest
    # of the validators (2 = operational error / missing dep).
    sys.exit(
        "[ERR] PyYAML not available; install with:\n"
        "      python3 -m pip install 'PyYAML==6.0.3'\n"
        "      (or run under `uvx --with pyyaml==6.0.3` to scope the dep)"
    )

workflows_dir = Path(sys.argv[1])
fmt = sys.argv[2]


def matrix_combinations(matrix: dict[str, Any]) -> list[list[tuple[str, str]]]:
    """Expand a GitHub Actions `strategy.matrix` mapping into the list of
    combinations GitHub uses for check-context names. Includes the
    standard `include:` augmentation rule; ignores `exclude:` (rare in
    this repo)."""
    if not matrix:
        return [[]]
    keys = [k for k in matrix.keys() if k not in {"include", "exclude"}]
    axes = []
    for key in keys:
        values = matrix[key]
        if not isinstance(values, list):
            continue
        axes.append([(key, str(v)) for v in values])
    if not axes:
        combos = [[]]
    else:
        combos = [[]]
        for axis in axes:
            combos = [c + [v] for c in combos for v in axis]
    for inc in matrix.get("include", []) or []:
        if isinstance(inc, dict):
            combos.append([(k, str(v)) for k, v in inc.items()])
    return combos


def render_combo(combo: list[tuple[str, str]]) -> str:
    """Mirror GitHub's display: `(value1, value2, ...)` in matrix key order."""
    if not combo:
        return ""
    return "(" + ", ".join(v for _, v in combo) + ")"


def expand_template(template: str, combo: list[tuple[str, str]]) -> str:
    """Substitute `${{ matrix.<key> }}` references in a job display name
    with the concrete combo value. Other expressions are left intact."""
    result = template
    for key, value in combo:
        for token in ("${{ matrix." + key + " }}", "${{matrix." + key + "}}"):
            result = result.replace(token, value)
    return result


entries: list[dict[str, Any]] = []
for yml in sorted(workflows_dir.glob("*.yml")):
    data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
    workflow_name = data.get("name") or yml.stem
    jobs = data.get("jobs") or {}
    triggers = data.get(True, data.get("on")) or {}
    # PyYAML parses `on:` as the boolean `True` because YAML 1.1 treats
    # `on/off` as booleans. Fall back to the string key when present.
    if isinstance(triggers, dict):
        trigger_keys = sorted(triggers.keys())
    elif isinstance(triggers, list):
        trigger_keys = [str(t) for t in triggers]
    else:
        trigger_keys = [str(triggers)] if triggers else []
    for job_key, job_body in jobs.items():
        if not isinstance(job_body, dict):
            continue
        display_template = job_body.get("name") or job_key
        matrix = (job_body.get("strategy") or {}).get("matrix") or {}
        combos = matrix_combinations(matrix)
        for combo in combos:
            display = expand_template(str(display_template), combo).strip()
            suffix = render_combo(combo)
            if suffix and suffix not in display:
                display = f"{display} {suffix}".strip()
            entry = {
                "workflow_file": yml.name,
                "workflow_name": workflow_name,
                "job_key": job_key,
                "job_display": display,
                "context": f"{workflow_name} / {display}",
                "triggers": trigger_keys,
                "matrix": dict(combo) if combo else None,
            }
            entries.append(entry)

if fmt == "json":
    print(json.dumps({"count": len(entries), "contexts": entries}, indent=2))
else:
    width = max((len(e["workflow_name"]) for e in entries), default=20)
    print(f"{'WORKFLOW'.ljust(width)}  JOB  →  CONTEXT (triggers)")
    for e in entries:
        triggers = ",".join(e["triggers"]) if e["triggers"] else "-"
        print(
            f"{e['workflow_name'].ljust(width)}  "
            f"{e['job_key']}  →  {e['context']}  ({triggers})"
        )
PY
