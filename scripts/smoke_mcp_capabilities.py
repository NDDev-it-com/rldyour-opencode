#!/usr/bin/env python3
"""MCP capability smoke probe.

Parse `opencode.json.mcp` and verify each declared server responds:

- remote (https/sse): TCP + HTTP probe via urllib (per-server timeout
  5 s). Accepts any HTTP status as "alive" — a 401 / 403 from an
  auth-gated endpoint still proves the server answered.
- local (command-based): subprocess spawn the launcher with the
  declared command for a short window. If the launcher exits non-zero
  inside the window OR the binary is missing, the server is reported
  as "skip" (fresh-checkout safety — uvx / bunx / dart may not yet be
  installed) rather than "fail". If the process is still alive after
  the window, it is "alive".

Designed for smoke health-checks on developer machines and in CI.
Stdlib only; never imports anything outside Python 3.11+ stdlib.

Exit codes:
  0  All reachable servers passed; unreachable servers were "skip".
  1  At least one server failed (process exited with error inside
     the window, or HTTP probe failed with a network-level error).
  2  Bad input / opencode.json missing / malformed.

Usage:
    python3 scripts/smoke_mcp_capabilities.py            # text report
    python3 scripts/smoke_mcp_capabilities.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OPENCODE_JSON = PROJECT_ROOT / "opencode.json"

REMOTE_TIMEOUT_SECONDS = 8.0
LOCAL_PROBE_WINDOW_SECONDS = 3.0


def probe_remote(name: str, url: str) -> dict[str, Any]:
    """Try HEAD first, then GET. Some MCP endpoints (notably grep.app and
    OpenAI docs) reject HEAD and only respond on GET or POST initialize.
    HEAD-then-GET keeps the probe cheap for compliant servers while still
    detecting reachability for HEAD-rejecting ones."""
    started = time.monotonic()
    last_err: str | None = None
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=REMOTE_TIMEOUT_SECONDS) as resp:
                return {
                    "name": name,
                    "kind": "remote",
                    "url": url,
                    "status": "alive",
                    "method": method,
                    "http": resp.status,
                    "latency_ms": int((time.monotonic() - started) * 1000),
                }
        except urllib.error.HTTPError as e:
            # Any HTTP status — including auth-gated 401/403 and method-
            # rejecting 405 — proves the server answered.
            return {
                "name": name,
                "kind": "remote",
                "url": url,
                "status": "alive",
                "method": method,
                "http": e.code,
                "latency_ms": int((time.monotonic() - started) * 1000),
            }
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as e:
            last_err = str(e)
            continue
    return {
        "name": name,
        "kind": "remote",
        "url": url,
        "status": "fail",
        "error": last_err or "unreachable",
        "latency_ms": int((time.monotonic() - started) * 1000),
    }


def probe_local(name: str, command: list[str]) -> dict[str, Any]:
    started = time.monotonic()
    launcher = command[0] if command else ""
    if not launcher or shutil.which(launcher) is None:
        return {
            "name": name,
            "kind": "local",
            "command": command,
            "status": "skip",
            "reason": f"launcher {launcher!r} not on PATH",
        }
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(PROJECT_ROOT),
        )
    except (OSError, FileNotFoundError) as e:
        return {
            "name": name,
            "kind": "local",
            "command": command,
            "status": "fail",
            "error": str(e),
        }
    try:
        rc = proc.wait(timeout=LOCAL_PROBE_WINDOW_SECONDS)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        return {
            "name": name,
            "kind": "local",
            "command": command,
            "status": "alive",
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        }
    return {
        "name": name,
        "kind": "local",
        "command": command,
        "status": "fail" if rc != 0 else "alive",
        "exit_code": rc,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
    }


def main() -> int:
    desc = (__doc__ or "MCP capability smoke probe.").splitlines()[0]
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    try:
        cfg = json.loads(OPENCODE_JSON.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        print(f"opencode.json not found at {OPENCODE_JSON}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"opencode.json is not valid JSON: {e}", file=sys.stderr)
        return 2

    mcp = cfg.get("mcp", {}) or {}
    if not isinstance(mcp, dict) or not mcp:
        print("opencode.json has no `mcp` section or it is empty", file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    for name in sorted(mcp.keys()):
        entry = mcp[name] or {}
        if entry.get("enabled") is False:
            continue
        kind = entry.get("type")
        if kind == "remote":
            url = str(entry.get("url") or "")
            results.append(probe_remote(name, url) if url else {
                "name": name, "kind": "remote", "status": "fail", "error": "missing url",
            })
        elif kind == "local":
            command = entry.get("command") or []
            results.append(probe_local(name, list(command)))
        else:
            results.append({"name": name, "kind": kind or "?", "status": "fail", "error": "unknown type"})

    failed = [r for r in results if r["status"] == "fail"]

    if args.json:
        json.dump({"results": results, "failed": len(failed), "total": len(results)}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"MCP smoke: {len(results)} servers checked, {len(failed)} failed")
        for r in results:
            tag = {"alive": "[OK]", "skip": "[SKIP]", "fail": "[FAIL]"}[r["status"]]
            detail = ""
            if "http" in r:
                detail = f" http={r['http']} latency={r.get('latency_ms')}ms"
            elif "exit_code" in r:
                detail = f" exit={r['exit_code']}"
            elif "reason" in r:
                detail = f" ({r['reason']})"
            elif "error" in r:
                detail = f" error={r['error']}"
            print(f"  {tag} {r['name']:<22} kind={r.get('kind')}{detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
