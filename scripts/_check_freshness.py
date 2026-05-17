#!/usr/bin/env python3
"""Registry freshness probe for pinned MCP dependencies.

Reads the JSON envelope emitted by `_extract_pins.py` from stdin and
queries each pin's upstream registry to determine whether the pinned
version is current or stale:

- npm: GET https://registry.npmjs.org/<name>/latest -> { version }
- PyPI: GET https://pypi.org/pypi/<name>/json -> { info: { version } }
- dart: skipped (system Dart SDK; no upstream version probe wired here)

Each network call has a 5 second timeout. Failures are reported per-pin
as `source: "error"` so an outage of one registry never blocks the
report on the other.

Exit codes:
  0  all pins current or skipped
  1  at least one pin is stale
  2  network failures prevented a comparison (treated as not-stale-but-
     not-current; CI workflows can opt into failing-on-2 via `--strict`).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from typing import Any

NETWORK_TIMEOUT_SECONDS = 5.0

_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[.-].*)?$")


def _semver_tuple(version: str) -> tuple[int, int, int] | None:
    m = _SEMVER_RE.match(version.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def probe_npm(name: str) -> tuple[str | None, str | None]:
    """Return (latest_version, error). Empty error means success."""
    try:
        data = _fetch_json(f"https://registry.npmjs.org/{name}/latest")
        version = data.get("version")
        if isinstance(version, str):
            return version, None
        return None, f"unexpected response shape: {type(data).__name__}"
    except urllib.error.HTTPError as exc:
        return None, f"http {exc.code}"
    except urllib.error.URLError as exc:
        return None, f"network: {exc.reason}"
    except (json.JSONDecodeError, TimeoutError, OSError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def probe_pypi(name: str) -> tuple[str | None, str | None]:
    try:
        data = _fetch_json(f"https://pypi.org/pypi/{name}/json")
        version = (data.get("info") or {}).get("version")
        if isinstance(version, str):
            return version, None
        return None, "unexpected response shape"
    except urllib.error.HTTPError as exc:
        return None, f"http {exc.code}"
    except urllib.error.URLError as exc:
        return None, f"network: {exc.reason}"
    except (json.JSONDecodeError, TimeoutError, OSError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def classify(current: str, latest: str | None) -> str:
    if latest is None:
        return "unknown"
    cur_t = _semver_tuple(current)
    new_t = _semver_tuple(latest)
    if cur_t is None or new_t is None:
        return "unknown" if current != latest else "current"
    if cur_t == new_t:
        return "current"
    if cur_t < new_t:
        return "stale"
    return "ahead"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 2 when at least one pin failed the freshness probe (network error)",
    )
    args = parser.parse_args()

    try:
        envelope = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"[ERR] failed to read pin envelope from stdin: {exc}", file=sys.stderr)
        return 2

    pins = envelope.get("pins") or []
    out_pins: list[dict[str, Any]] = []
    stale = 0
    errors = 0

    for entry in pins:
        kind = entry.get("kind")
        name = entry.get("name", "")
        current = entry.get("version", "")
        latest: str | None = None
        error: str | None = None
        source = "skip"

        if kind == "npm" and name:
            source = "npm"
            latest, error = probe_npm(name)
        elif kind == "pypi" and name:
            source = "pypi"
            latest, error = probe_pypi(name)
        else:
            source = kind or "skip"

        status = classify(current, latest) if latest else ("error" if error else "skip")
        if status == "stale":
            stale += 1
        if error:
            errors += 1

        out_pins.append(
            {
                **entry,
                "latest": latest,
                "status": status,
                "source": source,
                **({"error": error} if error else {}),
            }
        )

    result = {
        "pins": out_pins,
        "count": len(out_pins),
        "stale": stale,
        "errors": errors,
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")

    if stale:
        return 1
    if args.strict and errors:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
