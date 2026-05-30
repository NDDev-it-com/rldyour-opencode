#!/usr/bin/env python3
"""MCP capability smoke probe with `--mode` profiles.

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

`--mode` selects which probe class fires:

- `all` (default): probe every server. Backward compatible with the
  pre-0.12.2 single-mode invocation.
- `static`: parse `opencode.json` only; no network, no spawn. Outputs
  the server roster + their declared profile (if known). Always safe in
  CI and on fresh checkouts.
- `local-launch`: spawn only `type: local` servers.
- `remote-head`: probe only `type: remote` endpoints via HEAD/GET.

The CI mapping (see audit P1-4 and `docs/security/mcp-trust-boundaries.md`):

  PR runs (`validate.yml`):    `--mode static` (parse-only gate)
  Scheduled (`dependency-check.yml`): both `--mode remote-head` AND
                                `--mode local-launch` as separate
                                `continue-on-error` steps so a transient
                                outage cannot block the weekly report.
  Manual/live:                  `--mode all` (or a future RPC handshake
                                — not yet wired; OpenCode's MCP `initialize`
                                round-trip would close the indeterminate
                                category but adds dependency cost).

Stdlib only; never imports anything outside Python 3.11+ stdlib.

Exit codes:
  0  All reachable servers passed; unreachable / skipped servers were
     either secrets-required (and the secret was absent) or had no
     launcher on PATH.
  1  At least one server failed (process exited with error inside
     the window, or HTTP probe failed with a network-level error).
  2  Bad input / opencode.json missing / malformed.

Usage:
    python3 scripts/smoke_mcp_capabilities.py                  # mode=all, text
    python3 scripts/smoke_mcp_capabilities.py --json           # mode=all, json
    python3 scripts/smoke_mcp_capabilities.py --mode static
    python3 scripts/smoke_mcp_capabilities.py --mode local-launch --json
    python3 scripts/smoke_mcp_capabilities.py --mode remote-head --json
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
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OPENCODE_JSON = PROJECT_ROOT / "opencode.json"
PROFILES_JSON = PROJECT_ROOT / "references" / "mcp-profiles.json"

REMOTE_TIMEOUT_SECONDS = 8.0
LOCAL_PROBE_WINDOW_SECONDS = 3.0

VALID_MODES = ("all", "static", "local-launch", "remote-head")


def _validate_remote_url(name: str, url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{name}: remote MCP URL must be absolute https")
    if parsed.username or parsed.password:
        raise ValueError(f"{name}: remote MCP URL must not include credentials")
    return url


def _load_profiles() -> dict[str, str]:
    """Return a `{server: profile}` lookup. Empty when the profiles file is
    absent so callers can degrade gracefully on fresh archives."""
    if not PROFILES_JSON.exists():
        return {}
    try:
        data = json.loads(PROFILES_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    out: dict[str, str] = {}
    for profile_name, body in (data.get("profiles") or {}).items():
        for server in body.get("members") or []:
            out[server] = profile_name
    return out


def probe_remote(name: str, url: str) -> dict[str, Any]:
    """Try HEAD first, then GET. Some MCP endpoints (notably grep.app and
    OpenAI docs) reject HEAD and only respond on GET or POST initialize.
    HEAD-then-GET keeps the probe cheap for compliant servers while still
    detecting reachability for HEAD-rejecting ones."""
    started = time.monotonic()
    last_err: str | None = None
    try:
        url = _validate_remote_url(name, url)
    except ValueError as e:
        return {
            "name": name,
            "kind": "remote",
            "url": url,
            "status": "fail",
            "error": str(e),
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method)
            # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
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
    """Spawn the launcher with stdin redirected to DEVNULL and observe
    the process for LOCAL_PROBE_WINDOW_SECONDS.

    A real MCP stdio server is supposed to read JSON-RPC frames from
    stdin and reply on stdout — it should never cleanly exit before
    the window elapses just because nothing is sending requests.
    Therefore only `TimeoutExpired` (still running) counts as `alive`.
    Any clean exit inside the window is reported as `indeterminate`
    (the process printed `--help` or a version banner and exited; we
    cannot prove the server actually started its read loop). A non-zero
    exit is `fail`.

    This semantic catches a class of failure that the previous
    `exit_code == 0 → alive` rule missed: a broken local MCP launcher
    that prints a help message and exits 0 would pass undetected."""
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
    # Exited cleanly inside the window — distinguish broken (rc != 0)
    # from indeterminate (rc == 0; printed help/version then exited).
    return {
        "name": name,
        "kind": "local",
        "command": command,
        "status": "fail" if rc != 0 else "indeterminate",
        "exit_code": rc,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        **(
            {
                "reason": (
                    "process exited cleanly inside the probe window; a real "
                    "MCP stdio server should keep reading stdin instead"
                )
            }
            if rc == 0
            else {}
        ),
    }


def describe_static(name: str, entry: dict[str, Any], profile: str | None) -> dict[str, Any]:
    """Static-mode descriptor: no probe, just classify the entry."""
    kind = entry.get("type") or "?"
    descriptor: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "status": "static",
        "profile": profile or "unassigned",
    }
    if kind == "remote":
        descriptor["url"] = entry.get("url") or ""
    elif kind == "local":
        descriptor["command"] = entry.get("command") or []
    return descriptor


def main(argv: list[str] | None = None) -> int:
    desc = (__doc__ or "MCP capability smoke probe.").splitlines()[0]
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default="all",
        help=(
            "Probe profile: 'static' parses only, 'local-launch' spawns local "
            "entries, 'remote-head' probes remote endpoints, 'all' (default) "
            "does both probe classes."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON",
    )
    args = parser.parse_args(argv)

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

    profiles = _load_profiles()

    results: list[dict[str, Any]] = []
    skipped_by_mode: list[str] = []
    for name in sorted(mcp.keys()):
        entry = mcp[name] or {}
        if entry.get("enabled") is False:
            continue
        kind = entry.get("type")

        if args.mode == "static":
            results.append(describe_static(name, entry, profiles.get(name)))
            continue

        if kind == "remote":
            if args.mode == "local-launch":
                skipped_by_mode.append(name)
                continue
            url = str(entry.get("url") or "")
            results.append(
                probe_remote(name, url)
                if url
                else {"name": name, "kind": "remote", "status": "fail", "error": "missing url"}
            )
        elif kind == "local":
            if args.mode == "remote-head":
                skipped_by_mode.append(name)
                continue
            command = entry.get("command") or []
            results.append(probe_local(name, list(command)))
        else:
            results.append(
                {"name": name, "kind": kind or "?", "status": "fail", "error": "unknown type"}
            )

    failed = [r for r in results if r["status"] == "fail"]
    indeterminate = [r for r in results if r["status"] == "indeterminate"]

    if args.json:
        json.dump(
            {
                "mode": args.mode,
                "results": results,
                "failed": len(failed),
                "indeterminate": len(indeterminate),
                "total": len(results),
                "skipped_by_mode": skipped_by_mode,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        mode_label = f"mode={args.mode}"
        suffix = f", {len(indeterminate)} indeterminate" if indeterminate else ""
        scope = f"({len(skipped_by_mode)} skipped by mode)" if skipped_by_mode else ""
        print(
            f"MCP smoke [{mode_label}]: "
            f"{len(results)} servers checked, {len(failed)} failed{suffix} {scope}"
        )
        tag_map = {
            "alive": "[OK]",
            "skip": "[SKIP]",
            "fail": "[FAIL]",
            "indeterminate": "[?]",
            "static": "[STATIC]",
        }
        for r in results:
            tag = tag_map.get(r["status"], "[?]")
            detail = ""
            if "http" in r:
                detail = f" http={r['http']} latency={r.get('latency_ms')}ms"
            elif "exit_code" in r:
                detail = f" exit={r['exit_code']}"
            elif "profile" in r:
                detail = f" profile={r['profile']}"
            elif "reason" in r:
                detail = f" ({r['reason']})"
            elif "error" in r:
                detail = f" error={r['error']}"
            print(f"  {tag} {r['name']:<22} kind={r.get('kind')}{detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
