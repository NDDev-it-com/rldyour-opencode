#!/usr/bin/env python3
"""Validate GitHub Actions `uses:` pins in workflow files.

The repository policy is:

- external actions are pinned to immutable 40-character commit SHAs;
- each SHA pin carries an inline `# vX.Y.Z` comment naming the upstream tag;
- optional remote validation resolves that tag and checks it points at the SHA.

The remote mode intentionally verifies the tag/comment pair instead of asking
whether the tag is latest. Dependabot owns freshness; this script prevents the
more dangerous drift where a SHA and its human-readable version comment diverge.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<target>\S+)(?:\s+#\s*(?P<tag>\S+))?\s*$")
PINNED_RE = re.compile(r"^(?P<action>[^@\s]+)@(?P<sha>[0-9a-f]{40})$", re.IGNORECASE)
SEMVER_TAG_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


@dataclass(frozen=True)
class ActionPin:
    path: Path
    line_no: int
    action: str
    repo: str
    sha: str
    tag: str

    @property
    def label(self) -> str:
        return f"{self.path}:{self.line_no}: {self.action}@{self.sha} # {self.tag}"


def _workflow_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.glob("*.yml")))
            files.extend(sorted(path.glob("*.yaml")))
        else:
            print(f"[ERR] workflow path not found: {path}")
    return sorted(set(files))


def _is_local_or_docker_action(target: str) -> bool:
    return target.startswith("./") or target.startswith("docker://")


def _repo_from_action(action: str) -> str | None:
    parts = action.split("/")
    if len(parts) < 2:
        return None
    return "/".join(parts[:2])


def collect_action_pins(paths: list[Path]) -> tuple[list[ActionPin], int]:
    pins: list[ActionPin] = []
    errors = 0

    for path in _workflow_files(paths):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "uses:" not in line:
                continue
            match = USES_RE.match(line)
            if not match:
                print(f"[ERR] {path}:{line_no}: malformed uses line")
                errors += 1
                continue

            target = match.group("target")
            if _is_local_or_docker_action(target):
                continue

            pin = PINNED_RE.match(target)
            if not pin:
                print(f"[ERR] {path}:{line_no}: external action must use a 40-char SHA pin: {target}")
                errors += 1
                continue

            tag = match.group("tag")
            if not tag or not SEMVER_TAG_RE.match(tag):
                print(f"[ERR] {path}:{line_no}: SHA pin must include inline semver tag comment")
                errors += 1
                continue

            action = pin.group("action")
            repo = _repo_from_action(action)
            if repo is None:
                print(f"[ERR] {path}:{line_no}: cannot derive owner/repo from action {action!r}")
                errors += 1
                continue

            pins.append(
                ActionPin(
                    path=path,
                    line_no=line_no,
                    action=action,
                    repo=repo,
                    sha=pin.group("sha").lower(),
                    tag=tag,
                )
            )

    return pins, errors


def _resolve_tag(repo: str, tag: str, timeout: float) -> tuple[str | None, str | None]:
    url = f"https://github.com/{repo}.git"
    result = subprocess.run(
        ["git", "ls-remote", "--tags", url, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        return None, detail

    tag_sha: str | None = None
    deref_sha: str | None = None
    for raw in result.stdout.splitlines():
        fields = raw.split()
        if len(fields) != 2:
            continue
        sha, ref = fields
        if ref == f"refs/tags/{tag}^{{}}":
            deref_sha = sha.lower()
        elif ref == f"refs/tags/{tag}":
            tag_sha = sha.lower()

    resolved = deref_sha or tag_sha
    if resolved is None:
        return None, f"tag {tag} not found"
    return resolved, None


def validate_remote(pins: list[ActionPin], *, timeout: float) -> int:
    errors = 0
    cache: dict[tuple[str, str], tuple[str | None, str | None]] = {}

    for pin in pins:
        key = (pin.repo, pin.tag)
        if key not in cache:
            cache[key] = _resolve_tag(pin.repo, pin.tag, timeout)
        resolved, error = cache[key]
        if error is not None:
            print(f"[ERR] {pin.label}: cannot resolve {pin.repo}@{pin.tag}: {error}")
            errors += 1
            continue
        if resolved != pin.sha:
            print(f"[ERR] {pin.label}: tag resolves to {resolved}, not pinned SHA")
            errors += 1

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Workflow file or directory paths")
    parser.add_argument("--remote", action="store_true", help="Verify inline tags with git ls-remote")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-tag git ls-remote timeout")
    args = parser.parse_args(argv)

    pins, errors = collect_action_pins(args.paths)
    if args.remote and errors == 0:
        errors += validate_remote(pins, timeout=args.timeout)

    if errors:
        print(f"[ERR] GitHub Actions pin validation failed: {errors} error(s)")
        return 1

    mode = "static + remote" if args.remote else "static"
    print(f"[OK] GitHub Actions pins valid ({len(pins)} pins, {mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
