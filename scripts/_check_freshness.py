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
import urllib.parse
import urllib.request
from typing import Any

NETWORK_TIMEOUT_SECONDS = 5.0
NPM_REGISTRY_HOST = "registry.npmjs.org"
PYPI_REGISTRY_HOST = "pypi.org"

_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)([.-].*)?$")
_PRERELEASE_TOKEN_RE = re.compile(
    r"(?:^|[.\-_])"
    r"(?:dev|rc|alpha|beta|pre|preview|nightly|snapshot|a\d+|b\d+|pre\d+)",
    re.IGNORECASE,
)


def _semver_parts(version: str) -> tuple[int, int, int, int] | None:
    """Parse a version into (major, minor, patch, stability).

    Stability is 1 for stable releases and 0 for prerelease/dev builds, so
    `1.3.0` sorts above `1.3.0.dev0` and `1.3.0-rc1`.
    """
    m = _SEMVER_RE.match(version.strip())
    if not m:
        return None
    suffix = m.group(4) or ""
    stability = 0 if _PRERELEASE_TOKEN_RE.search(suffix) else 1
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), stability


def _semver_tuple(version: str) -> tuple[int, int, int] | None:
    """Backward-compatible 3-part parser for callers that only display versions."""
    parts = _semver_parts(version)
    if parts is None:
        return None
    return parts[0], parts[1], parts[2]


def _validate_registry_url(url: str, *, allowed_host: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != allowed_host:
        raise ValueError(f"unexpected registry URL host for {allowed_host}: {url}")
    if parsed.username or parsed.password:
        raise ValueError(f"registry URL must not include credentials: {allowed_host}")
    return url


def _fetch_json(url: str, *, allowed_host: str) -> Any:
    url = _validate_registry_url(url, allowed_host=allowed_host)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
    with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def probe_npm(name: str) -> tuple[str | None, str | None]:
    """Return (latest_version, error). Empty error means success."""
    try:
        data = _fetch_json(f"https://{NPM_REGISTRY_HOST}/{name}/latest", allowed_host=NPM_REGISTRY_HOST)
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
        data = _fetch_json(f"https://{PYPI_REGISTRY_HOST}/pypi/{name}/json", allowed_host=PYPI_REGISTRY_HOST)
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
    cur = _semver_parts(current)
    new = _semver_parts(latest)
    if cur is None or new is None:
        return "unknown" if current != latest else "current"
    if cur == new:
        return "current"
    if cur < new:
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
