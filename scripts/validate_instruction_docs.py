#!/usr/bin/env python3
"""Verify the durable instruction docs (AGENTS.md, .claude/CLAUDE.md)
are present, non-trivially large, and contain the expected anchor
sections. Catches accidental deletion / truncation / template-only
state during a release.

Anchor sections come from the project's own documented contract:
- AGENTS.md must declare Project Purpose, Source Of Truth, Domain
  Boundaries, OpenCode Conventions, Validation Commands.
- .claude/CLAUDE.md must declare "What Claude Code should NOT do" and
  "Validation Claude Code MUST run before delivery".

Exit codes:
  0  Both docs present and complete.
  1  At least one doc missing or incomplete.

Usage:
    python3 scripts/validate_instruction_docs.py
    python3 scripts/validate_instruction_docs.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Each doc has a path, a minimum-byte threshold below which the file is
# considered "template-only", and a list of required anchor headings.
DOCS: list[dict[str, Any]] = [
    {
        "path": PROJECT_ROOT / "AGENTS.md",
        "min_bytes": 4096,
        "required_headings": (
            "## Project Purpose",
            "## Source Of Truth",
            "## Domain Boundaries",
            "## OpenCode Conventions",
            "## Validation Commands",
        ),
    },
    {
        "path": PROJECT_ROOT / ".claude" / "CLAUDE.md",
        "min_bytes": 1024,
        "required_headings": (
            "## Where canonical project knowledge lives",
            "## What Claude Code should NOT do",
            "## Validation Claude Code MUST run before delivery",
        ),
    },
]


def check_doc(spec: dict[str, Any]) -> dict[str, Any]:
    path: Path = spec["path"]
    rel = str(path.relative_to(PROJECT_ROOT)) if path.is_relative_to(PROJECT_ROOT) else str(path)
    if not path.exists():
        return {"path": rel, "status": "fail", "reason": "missing"}
    raw = path.read_bytes()
    if len(raw) < spec["min_bytes"]:
        return {
            "path": rel,
            "status": "fail",
            "reason": f"file is {len(raw)} bytes; expected at least {spec['min_bytes']}",
        }
    text = raw.decode("utf-8", errors="replace")
    missing = [h for h in spec["required_headings"] if not re.search(rf"^{re.escape(h)}$", text, re.MULTILINE)]
    if missing:
        return {
            "path": rel,
            "status": "fail",
            "reason": "missing required headings",
            "missing_headings": missing,
        }
    return {
        "path": rel,
        "status": "ok",
        "bytes": len(raw),
        "headings": len(spec["required_headings"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    results = [check_doc(spec) for spec in DOCS]
    failed = [r for r in results if r["status"] == "fail"]

    if args.json:
        json.dump({"results": results, "failed": len(failed), "total": len(results)}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"Instruction docs: {len(results)} checked, {len(failed)} failed")
        for r in results:
            tag = "[OK]" if r["status"] == "ok" else "[FAIL]"
            if r["status"] == "ok":
                detail = f"bytes={r['bytes']} headings={r['headings']}"
            else:
                detail = r.get("reason", "")
                if "missing_headings" in r:
                    detail += f" {r['missing_headings']}"
            print(f"  {tag} {r['path']}  {detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
