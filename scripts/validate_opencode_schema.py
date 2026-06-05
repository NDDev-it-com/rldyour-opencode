#!/usr/bin/env python3
"""Validate opencode.json against a pinned OpenCode JSON Schema snapshot.

The schema lives at https://opencode.ai/config.json and is vendored under
references/opencode-config.schema.v<version>.json so this validator can run
offline and produce deterministic CI results even when opencode.ai is
unreachable. The static path-based validator in `_validate_helpers.py` keeps
checking project-specific invariants (forbidden frontmatter, canonical
permission keys, action pins). This script is the complementary structural
gate against the upstream contract.

Usage:
    python3 scripts/validate_opencode_schema.py [--schema PATH] [--config PATH] [--offline|--live]

Exits 0 when the config validates cleanly, 1 when it does not, 2 on
operational errors (missing schema file, missing jsonschema library, etc.).
The runner is responsible for invoking with `uvx --with jsonschema==4.26.0`
so the dependency is pinned the same way pytest/PyYAML are.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = REPO_ROOT / "references" / "opencode-config.schema.v1.16.0.json"
DEFAULT_CONFIG = REPO_ROOT / "opencode.json"
# Every external $ref the vendored OpenCode schema points at MUST have a
# matching local snapshot in this map. The validator builds a Registry
# from these pairs so resolution stays offline — no opencode.ai or
# models.dev network round-trip on every CI run. Add a new entry when
# the upstream schema starts referencing a new external resource.
EXTERNAL_REF_VENDORED_AT: dict[str, Path] = {
    "https://models.dev/model-schema.json": REPO_ROOT / "references" / "models.dev-model-schema.json",
}


JsonValue = (
    "str | int | float | bool | None | dict[str, 'JsonValue'] | list['JsonValue']"
)


def _load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise TypeError(f"{path}: top-level JSON must be an object")
    return data


def _format_error_path(error: object) -> str:
    """Render a jsonschema ValidationError path as `$.foo.bar[0]`."""
    parts = ["$"]
    for piece in getattr(error, "absolute_path", []):
        if isinstance(piece, int):
            parts.append(f"[{piece}]")
        else:
            parts.append(f".{piece}")
    return "".join(parts)


def validate(config_path: Path, schema_path: Path, *, live: bool = False) -> int:
    if not schema_path.exists():
        print(f"[ERR] schema not found: {schema_path}", file=sys.stderr)
        return 2
    if not config_path.exists():
        print(f"[ERR] config not found: {config_path}", file=sys.stderr)
        return 2

    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
        from referencing.exceptions import Unresolvable
        from referencing.jsonschema import DRAFT202012
    except ImportError:
        print(
            "[ERR] jsonschema/referencing library not available. "
            "Run with `uvx --with jsonschema==4.26.0 python3 scripts/validate_opencode_schema.py`",
            file=sys.stderr,
        )
        return 2

    schema = _load_json(schema_path)
    config = _load_json(config_path)

    if live:
        print(
            "[ERR] --live is intentionally not implemented in CI. Refresh the "
            "vendored schema explicitly, commit it, then run --offline.",
            file=sys.stderr,
        )
        return 2

    # Build an offline Registry from the EXTERNAL_REF_VENDORED_AT map so
    # any `$ref: https://...` inside the vendored schema resolves to the
    # local snapshot instead of triggering a network fetch. Audit P0-2
    # found that `https://models.dev/model-schema.json` was the only
    # external ref; the contract now stays explicit — every URL the
    # schema points at must have a vendored counterpart. If a new URL
    # appears upstream the validator will fail with Unresolvable, which
    # is exactly the signal we want.
    resources: list[tuple[str, Resource[dict[str, object]]]] = []
    for uri, vendored_path in EXTERNAL_REF_VENDORED_AT.items():
        if not vendored_path.exists():
            print(
                f"[ERR] external ref {uri!r} expects vendored file at "
                f"{vendored_path}, which is missing. Run "
                f"`curl -fsSL {uri} -o {vendored_path.relative_to(REPO_ROOT)}` "
                f"and commit the snapshot.",
                file=sys.stderr,
            )
            return 2
        resource = Resource.from_contents(
            _load_json(vendored_path),
            default_specification=DRAFT202012,
        )
        resources.append((uri, resource))
    registry: Registry[dict[str, object]] = Registry().with_resources(resources)  # type: ignore[arg-type]

    # `iter_errors` is typed to `_JsonParameter` which is a recursive JSON
    # union; mypy and Pyright cannot unify it with our `dict[str, object]`
    # bound. The runtime contract is identical, so we cast for the call.
    validator = Draft202012Validator(schema, registry=registry)  # type: ignore[arg-type]
    # Sort by string-normalised path segments — quality review F-2 noted
    # that `absolute_path` is a deque of mixed `int` (array indices) and
    # `str` (object keys), and Python 3 raises TypeError when sorting
    # `int < str`. Stringifying every segment gives a stable, predictable
    # ordering for both kinds of error locations.
    try:
        errors = sorted(  # type: ignore[arg-type]
            validator.iter_errors(config),  # type: ignore[arg-type]
            key=lambda e: [str(p) for p in e.absolute_path],
        )
    except Unresolvable as exc:
        print(
            f"[ERR] schema reference could not be resolved offline: {exc}. "
            f"Add the URL to EXTERNAL_REF_VENDORED_AT and vendor the snapshot.",
            file=sys.stderr,
        )
        return 2
    if not errors:
        print(f"[OK] {config_path.name} validates against {schema_path.name}")
        return 0

    print(
        f"[FAIL] {config_path.name} has {len(errors)} schema violation(s) "
        f"against {schema_path.name}:",
        file=sys.stderr,
    )
    for err in errors:
        location = _format_error_path(err)
        print(f"  - {location}: {err.message}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate opencode.json against a pinned OpenCode JSON Schema snapshot.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help=f"Path to the JSON Schema file (default: {DEFAULT_SCHEMA.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to the OpenCode config file (default: {DEFAULT_CONFIG.relative_to(REPO_ROOT)})",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--offline",
        action="store_true",
        help="Use only vendored schema snapshots. This is the default.",
    )
    mode.add_argument(
        "--live",
        action="store_true",
        help="Reserved for future explicit live schema refresh; currently fails closed.",
    )
    args = parser.parse_args(argv)
    _ = args.offline
    return validate(args.config, args.schema, live=args.live)


if __name__ == "__main__":
    raise SystemExit(main())
