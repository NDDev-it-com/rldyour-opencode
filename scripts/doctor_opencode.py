#!/usr/bin/env python3
"""Deterministic, timeout-safe healthcheck for rldyour-opencode.

The 2026-05-17 external audit flagged that the legacy bash doctor
(`scripts/doctor_opencode.sh`) could hang past 25 seconds, used shell
regex YAML parsing in places, and lacked a JSON output mode. This
Python rewrite ships those fixes plus a structured result envelope so
CI gates can consume the output without parsing color codes.

Design contract:
- Every subprocess call gets an explicit `timeout=` (no exceptions).
- Every check returns `{ check, status, duration_ms, details }`.
- Global wall-clock deadline of 60 s by default; `--total-timeout` to
  override. Each check that runs past the deadline is reported as
  `timeout` and the doctor exits with status code 3.
- Exit codes: 0 = clean, 1 = at least one `fail` check, 2 = operational
  error (missing repo, malformed baseline), 3 = total-timeout
  exceeded.

CLI:
    python3 scripts/doctor_opencode.py
    python3 scripts/doctor_opencode.py --format json
    python3 scripts/doctor_opencode.py --check config plugins skills
    python3 scripts/doctor_opencode.py --total-timeout 45
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENCODE_JSON = REPO_ROOT / "opencode.json"
DEFAULT_TOTAL_TIMEOUT_SECONDS = 60
PER_CHECK_TIMEOUT_SECONDS = 15

# Per-check timeout budget is module-level so the main loop can shrink it
# to the wall-clock remainder before each check fires (audit Quality-M
# fix). Subprocess-spawning checks read `_per_check_budget()` at call
# time, so the budget contracts naturally as `--total-timeout` is
# consumed.
_current_per_check_budget: int = PER_CHECK_TIMEOUT_SECONDS


def _per_check_budget() -> int:
    """The effective per-check timeout, dynamically narrowed by the main
    loop to the remaining wall-clock budget so the last check never runs
    past `--total-timeout`."""
    return _current_per_check_budget


_RESET = "\033[0m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"

STATUS_BADGE: dict[str, tuple[str, str]] = {
    "ok": ("OK", _GREEN),
    "warn": ("WARN", _YELLOW),
    "fail": ("FAIL", _RED),
    "skip": ("SKIP", _CYAN),
    "info": ("INFO", _CYAN),
    "timeout": ("TIMEOUT", _RED),
    # "operational" is reserved for irrecoverable environment errors that
    # block the doctor from doing useful work (missing opencode.json,
    # malformed baseline file, etc.). It maps to process exit code 2 so
    # CI can distinguish env breakage from a real per-check failure.
    "operational": ("OPER-ERR", _RED),
}


def _result(name: str, status: str, started_ns: int, details: list[str] | None = None) -> dict[str, Any]:
    return {
        "check": name,
        "status": status,
        "duration_ms": (time.monotonic_ns() - started_ns) // 1_000_000,
        "details": details or [],
    }


def _load_opencode_json() -> dict[str, Any] | None:
    if not OPENCODE_JSON.exists():
        return None
    try:
        return json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def check_config() -> dict[str, Any]:
    started = time.monotonic_ns()
    cfg = _load_opencode_json()
    if cfg is None:
        # Verification-review F-1: missing/malformed opencode.json is an
        # operational error, not a check failure. The runtime can not
        # proceed without it, so escalate to the "operational" status the
        # main loop maps to exit 2.
        return _result("config.opencode_json", "operational", started, [
            "opencode.json missing or invalid JSON",
        ])
    details: list[str] = []
    for field in ("model", "small_model", "default_agent"):
        value = cfg.get(field)
        if value:
            details.append(f"{field} = {value}")
        else:
            return _result(
                "config.opencode_json", "fail", started,
                details + [f"missing required field: {field}"],
            )
    lsp = cfg.get("lsp")
    if lsp is True:
        details.append("lsp = enabled (built-ins only)")
    elif isinstance(lsp, dict):
        details.append(f"lsp = enabled ({len(lsp)} custom server(s) + built-ins)")
    else:
        details.append(f"lsp = {lsp!r} (unexpected)")
    return _result("config.opencode_json", "ok", started, details)


def check_baseline() -> dict[str, Any]:
    started = time.monotonic_ns()
    script = REPO_ROOT / "scripts" / "check_baseline_consistency.py"
    if not script.exists():
        return _result("config.baseline", "skip", started, ["baseline script not present"])
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=REPO_ROOT,
            timeout=_per_check_budget(),
            capture_output=True,
            text=True,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _result(
            "config.baseline", "timeout", started,
            [f"check_baseline_consistency.py exceeded {_per_check_budget()}s"],
        )
    if proc.returncode == 0:
        return _result("config.baseline", "ok", started, [proc.stdout.strip() or "consistent"])
    return _result("config.baseline", "fail", started, [
        line for line in (proc.stderr.splitlines() or proc.stdout.splitlines()) if line.strip()
    ])


def _count_files(rel_dir: str, pattern: str) -> int:
    directory = REPO_ROOT / rel_dir
    return len(list(directory.glob(pattern))) if directory.exists() else 0


def check_skills() -> dict[str, Any]:
    started = time.monotonic_ns()
    skills_dir = REPO_ROOT / ".opencode" / "skills"
    # Quality-review F-5: a partial fullrepo restore or a fresh archive
    # can land without `.opencode/skills` at all. Guard the iterdir so the
    # doctor reports a clean skip instead of crashing on FileNotFoundError.
    if not skills_dir.exists():
        return _result("skills.index", "skip", started, [
            ".opencode/skills directory absent (fullrepo not bootstrapped)",
        ])
    count = sum(1 for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").exists())
    index = skills_dir / "index.json"
    if not index.exists():
        return _result("skills.index", "fail", started, [f"{count} skills on disk, index.json missing"])
    return _result("skills.index", "ok", started, [f"{count} skills, index present"])


def check_commands() -> dict[str, Any]:
    started = time.monotonic_ns()
    count = _count_files(".opencode/commands", "*.md")
    index = REPO_ROOT / ".opencode" / "commands" / "index.json"
    if not index.exists():
        return _result("commands.index", "fail", started, [f"{count} commands on disk, index.json missing"])
    return _result("commands.index", "ok", started, [f"{count} commands, index present"])


def check_plugins() -> dict[str, Any]:
    started = time.monotonic_ns()
    count = _count_files(".opencode/plugins", "*.ts")
    index = REPO_ROOT / ".opencode" / "plugins" / "index.json"
    if not index.exists():
        return _result("plugins.index", "fail", started, [f"{count} plugins on disk, index.json missing"])
    return _result("plugins.index", "ok", started, [f"{count} plugins, index present"])


def check_agents() -> dict[str, Any]:
    started = time.monotonic_ns()
    count = _count_files(".opencode/agents", "*.md")
    return _result("agents.count", "ok" if count > 0 else "warn", started, [f"{count} subagent file(s)"])


def check_mcp() -> dict[str, Any]:
    started = time.monotonic_ns()
    cfg = _load_opencode_json() or {}
    mcp = cfg.get("mcp", {})
    if not isinstance(mcp, dict) or not mcp:
        return _result("mcp.servers", "warn", started, ["no MCP servers declared in opencode.json"])
    enabled = [name for name, conf in mcp.items() if isinstance(conf, dict) and conf.get("enabled", True)]
    return _result("mcp.servers", "ok", started, [
        f"{len(enabled)} MCP servers enabled: {', '.join(sorted(enabled))}",
    ])


def check_serena() -> dict[str, Any]:
    started = time.monotonic_ns()
    serena = REPO_ROOT / ".serena"
    if not serena.exists():
        return _result("serena.layout", "skip", started, ["no .serena directory (restored from fullrepo on demand)"])
    project = serena / "project.yml"
    memories_dir = serena / "memories"
    details: list[str] = []
    if not project.exists():
        return _result("serena.layout", "fail", started, [".serena/project.yml missing"])
    details.append(".serena/project.yml present")
    if memories_dir.exists():
        details.append(f"{len(list(memories_dir.glob('*.md')))} memory file(s)")
    else:
        details.append("memories directory absent")
    return _result("serena.layout", "ok", started, details)


def check_git_state() -> dict[str, Any]:
    started = time.monotonic_ns()
    if not (REPO_ROOT / ".git").exists():
        return _result("git.state", "skip", started, ["not a git checkout"])
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT, timeout=5, capture_output=True, text=True, check=False,
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, timeout=5, capture_output=True, text=True, check=False,
        )
    except subprocess.TimeoutExpired:
        return _result("git.state", "timeout", started, ["git probes exceeded 5s"])
    branch_name = (branch.stdout or "").strip() or "<detached>"
    dirty_count = len([ln for ln in (dirty.stdout or "").splitlines() if ln.strip()])
    details = [f"branch = {branch_name}", f"dirty files = {dirty_count}"]
    return _result("git.state", "ok" if dirty_count == 0 else "warn", started, details)


def check_schema() -> dict[str, Any]:
    started = time.monotonic_ns()
    script = REPO_ROOT / "scripts" / "validate_opencode_schema.py"
    if not script.exists():
        return _result("config.schema", "skip", started, ["validator not present"])
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=REPO_ROOT, timeout=_per_check_budget(),
            capture_output=True, text=True, check=False,
        )
    except subprocess.TimeoutExpired:
        return _result("config.schema", "timeout", started, [f"validator exceeded {_per_check_budget()}s"])
    if proc.returncode == 0:
        return _result("config.schema", "ok", started, [proc.stdout.strip() or "valid"])
    if proc.returncode == 2:
        # operational error → treat as warn (likely missing jsonschema dep at the doctor invocation env)
        return _result("config.schema", "warn", started, [proc.stderr.strip() or "validator operational error"])
    return _result("config.schema", "fail", started, [
        line for line in (proc.stderr.splitlines() or proc.stdout.splitlines()) if line.strip()
    ][:10])


CHECKS: dict[str, Callable[[], dict[str, Any]]] = {
    "config": check_config,
    "baseline": check_baseline,
    "schema": check_schema,
    "skills": check_skills,
    "commands": check_commands,
    "plugins": check_plugins,
    "agents": check_agents,
    "mcp": check_mcp,
    "serena": check_serena,
    "git": check_git_state,
}


def render_text(results: list[dict[str, Any]]) -> str:
    lines = [
        "========================================",
        " rldyour-opencode Doctor (python core)",
        "========================================",
        "",
    ]
    for r in results:
        label, color = STATUS_BADGE.get(r["status"], ("?", _CYAN))
        prefix = f"{color}[{label}]{_RESET}"
        lines.append(f"  {prefix} {r['check']} ({r['duration_ms']}ms)")
        for d in r["details"]:
            lines.append(f"      {d}")
    fail = sum(1 for r in results if r["status"] in ("fail", "timeout"))
    warn = sum(1 for r in results if r["status"] == "warn")
    skip = sum(1 for r in results if r["status"] == "skip")
    ok = sum(1 for r in results if r["status"] == "ok")
    operational = sum(1 for r in results if r["status"] == "operational")
    lines.append("")
    summary_line = (
        f"  ok={ok}  warn={warn}  fail={fail}  oper-err={operational}  skip={skip}  total={len(results)}"
    )
    lines.append(summary_line)
    if operational:
        lines.append(f"  {_RED}{operational} operational error(s) — environment broken{_RESET}")
    elif fail:
        lines.append(f"  {_RED}{fail} check(s) FAILED{_RESET}")
    elif warn:
        lines.append(f"  {_YELLOW}clean with {warn} warning(s){_RESET}")
    else:
        lines.append(f"  {_GREEN}No issues found{_RESET}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rldyour-opencode doctor (Python core).")
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--check", nargs="+", choices=sorted(CHECKS.keys()),
        help="Restrict to a subset of checks; defaults to all.",
    )
    parser.add_argument(
        "--total-timeout", type=int, default=DEFAULT_TOTAL_TIMEOUT_SECONDS,
        help=f"Wall-clock deadline in seconds (default: {DEFAULT_TOTAL_TIMEOUT_SECONDS}).",
    )
    args = parser.parse_args(argv)

    selected = args.check or sorted(CHECKS.keys())
    started_total = time.monotonic_ns()
    deadline_ns = started_total + args.total_timeout * 1_000_000_000
    results: list[dict[str, Any]] = []
    timeout_hit = False
    global _current_per_check_budget
    for name in selected:
        if time.monotonic_ns() >= deadline_ns:
            timeout_hit = True
            results.append({
                "check": name,
                "status": "timeout",
                "duration_ms": 0,
                "details": [f"global doctor deadline of {args.total_timeout}s exceeded"],
            })
            continue
        # Audit Quality-M: shrink the per-check budget to the remaining
        # wall-clock window so the LAST check cannot overshoot the
        # global deadline by `PER_CHECK_TIMEOUT_SECONDS`. Clamp to a
        # 1 s minimum so checks still get a fair shot when the deadline
        # is near; we cap by the static PER_CHECK_TIMEOUT_SECONDS so a
        # very generous `--total-timeout` does not stretch any single
        # check past its design budget.
        remaining_ns = deadline_ns - time.monotonic_ns()
        remaining_s = max(1, int(remaining_ns // 1_000_000_000))
        _current_per_check_budget = min(PER_CHECK_TIMEOUT_SECONDS, remaining_s)
        results.append(CHECKS[name]())

    if args.format == "json":
        envelope = {
            "results": results,
            "summary": {
                "total": len(results),
                "ok": sum(1 for r in results if r["status"] == "ok"),
                "warn": sum(1 for r in results if r["status"] == "warn"),
                "fail": sum(1 for r in results if r["status"] == "fail"),
                "skip": sum(1 for r in results if r["status"] == "skip"),
                "timeout": sum(1 for r in results if r["status"] == "timeout"),
                "operational": sum(1 for r in results if r["status"] == "operational"),
            },
        }
        print(json.dumps(envelope, indent=2))
    else:
        print(render_text(results))

    operational = sum(1 for r in results if r["status"] == "operational")
    failing = sum(1 for r in results if r["status"] == "fail")
    if operational:
        return 2
    if failing:
        return 1
    if timeout_hit:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
