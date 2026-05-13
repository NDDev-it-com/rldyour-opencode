#!/usr/bin/env bash
# rldyour detect project checks
# Auto-detects project-native test, lint, typecheck, and build commands
set -euo pipefail

project_path="${1:-.}"
cd "$project_path" 2>/dev/null || true

echo "=== rldyour project check detection ==="
echo ""

DETECTIONS=0

detect_check() {
  local name="$1"
  local config_file="$2"
  shift 2
  local cmds=("$@")

  if [ -f "$config_file" ]; then
    for cmd in "${cmds[@]}"; do
      local pkg="${cmd%% *}"
      if command -v "$pkg" >/dev/null 2>&1; then
        echo "  $name: $cmd (detected from $config_file)"
        DETECTIONS=$((DETECTIONS + 1))
        return
      fi
    done
    echo "  $name: config found ($config_file) but runner not available"
    DETECTIONS=$((DETECTIONS + 1))
  fi
}

# Python
detect_check "test" "pyproject.toml" "pytest" "python -m pytest"
detect_check "lint" "pyproject.toml" "ruff check ." "flake8 ."
detect_check "typecheck" "pyproject.toml" "pyright" "mypy"

# TypeScript/JavaScript
detect_check "test" "package.json" "npm test" "pnpm test" "yarn test"
detect_check "lint" "package.json" "npm run lint" "pnpm lint" "yarn lint" "eslint ."
detect_check "typecheck" "tsconfig.json" "npx tsc --noEmit" "pnpm tsc --noEmit"

# Rust
detect_check "test" "Cargo.toml" "cargo test"
detect_check "lint" "Cargo.toml" "cargo clippy"
detect_check "typecheck" "Cargo.toml" "cargo check"

# Go
detect_check "test" "go.mod" "go test ./..."
detect_check "lint" "go.mod" "golangci-lint run"

# Dart/Flutter
detect_check "test" "pubspec.yaml" "flutter test" "dart test"
detect_check "lint" "pubspec.yaml" "dart analyze"

# Docker
detect_check "build" "Dockerfile" "docker build ."

echo ""
if [ "$DETECTIONS" -eq 0 ]; then
  echo "No language stack manifests found in this directory."
  echo "Marketplace / docs-only repositories should rely on:"
  echo "  - bash scripts/validate_config.sh"
  echo "  - python3 -m pytest scripts/tests/"
  echo "  - opencode debug config"
else
  echo "Note: Run detected commands manually or via /ry-start quality gates."
fi