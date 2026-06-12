#!/usr/bin/env bash
set -euo pipefail

APPLY=0
FORCE_PROJECT_INSTALL=0
GLOBAL_CONFIG=0
TARGET_DIR=${PWD}

usage() {
  cat <<'EOF'
Usage: scripts/install_system_opencode.sh [--dry-run|--apply] --target PATH [--force-project-install] [--global-config]

Installs or updates the rldyour OpenCode project configuration in a target
project. Existing files are backed up under .rldyour/backups/opencode/<timestamp>.

This script refuses to create a brand-new OpenCode project config unless
--force-project-install is explicit, so /ry-repair cannot silently pollute an
unrelated repository with opencode.json or .opencode files.

Use --global-config for ${XDG_CONFIG_HOME:-$HOME/.config}/opencode. That mode
also mirrors top-level OpenCode runtime directories such as commands/, skills/,
agents/, plugins/, package.json, and references/.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      APPLY=0
      ;;
    --apply)
      APPLY=1
      ;;
    --target)
      shift
      TARGET_DIR=${1:?--target requires a path}
      ;;
    --force-project-install)
      FORCE_PROJECT_INSTALL=1
      ;;
    --global-config)
      GLOBAL_CONFIG=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if ROOT=$(git -C "$SCRIPT_DIR/.." rev-parse --show-toplevel 2>/dev/null); then
  :
else
  ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
fi

TARGET_DIR=$(cd "$TARGET_DIR" && pwd)
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)

export RLDYOUR_OPENCODE_ROOT="$ROOT"
export RLDYOUR_OPENCODE_TARGET="$TARGET_DIR"
export RLDYOUR_OPENCODE_APPLY="$APPLY"
export RLDYOUR_OPENCODE_FORCE="$FORCE_PROJECT_INSTALL"
export RLDYOUR_OPENCODE_GLOBAL_CONFIG="$GLOBAL_CONFIG"
export RLDYOUR_OPENCODE_TIMESTAMP="$TIMESTAMP"

python3 <<'PY'
from __future__ import annotations

import filecmp
import os
import shutil
import sys
from pathlib import Path

source_root = Path(os.environ["RLDYOUR_OPENCODE_ROOT"]).resolve()
target = Path(os.environ["RLDYOUR_OPENCODE_TARGET"]).resolve()
apply = os.environ["RLDYOUR_OPENCODE_APPLY"] == "1"
force = os.environ["RLDYOUR_OPENCODE_FORCE"] == "1"
global_config = os.environ["RLDYOUR_OPENCODE_GLOBAL_CONFIG"] == "1"
timestamp = os.environ["RLDYOUR_OPENCODE_TIMESTAMP"]

project_paths = [
    (Path("opencode.json"), Path("opencode.json")),
    (Path(".opencode"), Path(".opencode")),
    (Path("AGENTS.md"), Path("AGENTS.md")),
]
global_paths = [
    (Path(".opencode/agents"), Path("agents")),
    (Path(".opencode/commands"), Path("commands")),
    (Path(".opencode/plugins"), Path("plugins")),
    (Path(".opencode/skills"), Path("skills")),
    (Path(".opencode/package.json"), Path("package.json")),
    (Path(".opencode/bun.lock"), Path("bun.lock")),
    (Path(".opencode/tsconfig.json"), Path("tsconfig.json")),
    (Path(".opencode/.gitignore"), Path(".gitignore")),
    (Path("references"), Path("references")),
]
source_paths = project_paths + (global_paths if global_config else [])
optional_source_paths = {Path("AGENTS.md")}
excluded_parts = {"node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "cache"}
excluded_suffixes = {".pyc"}
# macOS-only orchestrator skills: cmux (manaflow-ai/cmux) is a macOS
# application, so Linux/WSL/Windows installs never receive these skills.
MACOS_ONLY_SKILLS = {"cmux-orchestrator", "cmux-worker"}


def is_macos_only_skill_path(rel_parts: tuple[str, ...]) -> bool:
    if sys.platform == "darwin":
        return False
    for index, part in enumerate(rel_parts):
        if part == "skills" and index + 1 < len(rel_parts) and rel_parts[index + 1] in MACOS_ONLY_SKILLS:
            return True
    return False


def should_copy(path: Path) -> bool:
    rel_parts = path.relative_to(source_root).parts
    if any(part in excluded_parts for part in rel_parts):
        return False
    if is_macos_only_skill_path(rel_parts):
        return False
    return path.suffix not in excluded_suffixes


def copy_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True, exist_ok=True)
        for child in sorted(src.rglob("*")):
            if not should_copy(child):
                continue
            rel = child.relative_to(src)
            target_child = dst / rel
            if child.is_dir():
                target_child.mkdir(parents=True, exist_ok=True)
            elif child.is_file():
                target_child.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(child, target_child)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


if not target.exists() and apply and (force or global_config):
    target.mkdir(parents=True, exist_ok=True)
if not target.exists():
    raise SystemExit(f"target does not exist: {target}")

target_has_opencode = (
    (target / "opencode.json").exists()
    or (target / ".opencode").exists()
    or (global_config and ((target / "commands").exists() or (target / "skills").exists()))
)
if target != source_root and not target_has_opencode and not force and not global_config:
    raise SystemExit(
        f"{target}: no existing OpenCode config found. Re-run with --force-project-install "
        "to create opencode.json/.opencode in this project."
    )

actions: list[str] = []
backup_dir = target / ".rldyour" / "backups" / "opencode" / timestamp
for src_rel, dst_rel in source_paths:
    src = source_root / src_rel
    dst = target / dst_rel
    if not src.exists():
        if src_rel in optional_source_paths:
            actions.append(f"skip optional missing {src_rel}; restore fullrepo to install this agent-only file")
            continue
        raise SystemExit(f"missing source path: {src}")
    if dst.resolve() == src.resolve():
        actions.append(f"unchanged self path {dst_rel}")
        continue
    if dst.exists():
        actions.append(f"backup {dst_rel} -> {backup_dir / dst_rel}")
    actions.append(f"copy {src} -> {dst}")
    if apply:
        if dst.exists():
            backup_target = backup_dir / dst_rel
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            if dst.is_dir():
                if backup_target.exists():
                    shutil.rmtree(backup_target)
                shutil.copytree(dst, backup_target, ignore=shutil.ignore_patterns("node_modules", "__pycache__"))
            else:
                shutil.copy2(dst, backup_target)
        copy_path(src, dst)

for action in actions:
    print(action)
print("ok: OpenCode project config " + ("installed" if apply else "planned"))
PY
