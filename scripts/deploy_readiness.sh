#!/usr/bin/env bash
# rldyour deploy readiness check
# Checks if the project is ready for deployment
set -euo pipefail

target="${1:-local}"
failures=0
echo "=== rldyour deploy readiness: $target ==="
echo ""

# Git clean
dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ "$dirty" -gt 0 ]; then
  echo "FAIL: $dirty dirty files in working tree"
  failures=$((failures + 1))
else
  echo "OK: working tree clean"
fi

# On main branch
branch=$(git branch --show-current 2>/dev/null || echo "HEAD")
if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
  echo "OK: on $branch branch"
else
  echo "WARN: on $branch (expected main or master)"
fi

# Up to date with remote
ahead=$(git rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo '0')
behind=$(git rev-list --count 'HEAD..@{upstream}' 2>/dev/null || echo '0')
if [ "$ahead" -gt 0 ]; then
  echo "FAIL: $ahead commits ahead of upstream (push first)"
  failures=$((failures + 1))
elif [ "$behind" -gt 0 ]; then
  echo "FAIL: $behind commits behind upstream (pull first)"
  failures=$((failures + 1))
else
  echo "OK: up to date with upstream"
fi

# Serena memories
if [ -d ".serena/memories" ]; then
  mem_count=$(find ".serena/memories" -name '*.md' | wc -l | tr -d ' ')
  echo "OK: $mem_count Serena memory files"
else
  echo "WARN: no .serena/memories directory"
fi

# Detect project checks
echo ""
echo "--- Project checks ---"

# Test detection
for cmd in "npm test" "pnpm test" "yarn test" "cargo test" "go test ./..." "pytest" "dotnet test"; do
  pkg=$(echo "$cmd" | cut -d' ' -f1)
  if command -v "$pkg" >/dev/null 2>&1; then
    echo "Available: $cmd"
  fi
done

# Lint detection
for cmd in "npm run lint" "pnpm lint" "eslint ." "ruff check ." "golangci-lint run"; do
  pkg=$(echo "$cmd" | cut -d' ' -f1)
  if command -v "$pkg" >/dev/null 2>&1; then
    echo "Available: $cmd"
  fi
done

echo ""
if [ "$failures" -eq 0 ]; then
  echo "Deploy readiness: PASS"
  exit 0
else
  echo "Deploy readiness: FAIL ($failures failures)"
  exit 1
fi