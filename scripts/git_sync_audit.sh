#!/usr/bin/env bash
# rldyour git sync audit
# Audits git state: branch, upstream, dirty files, worktrees, stale branches
set -euo pipefail

echo "=== rldyour git sync audit ==="
echo ""

root="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
branch="$(git branch --show-current 2>/dev/null || echo 'HEAD')"

echo "Branch: $branch"
echo "Root: $root"
echo ""

# Dirty files
dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
echo "Dirty files: $dirty"
if [ "$dirty" -gt 0 ]; then
  git status --porcelain 2>/dev/null | head -20
  [ "$dirty" -gt 20 ] && echo "... ($((dirty - 20)) more)"
fi
echo ""

# Ahead/behind
ahead=$(git rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo '0')
behind=$(git rev-list --count 'HEAD..@{upstream}' 2>/dev/null || echo '0')
echo "Ahead of upstream: $ahead"
echo "Behind upstream: $behind"
echo ""

# Worktrees
wt_count=$(git worktree list 2>/dev/null | wc -l | tr -d ' ')
echo "Worktrees: $((wt_count - 1))"
if [ "$((wt_count - 1))" -gt 0 ]; then
  git worktree list 2>/dev/null | tail -n +2
fi
echo ""

# Stale branches (merged into main)
if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
  stale=$(git branch --merged HEAD 2>/dev/null | grep -v '^\*\|main\|master' | wc -l | tr -d ' ')
  if [ "$stale" -gt 0 ]; then
    echo "Stale branches (merged into $branch): $stale"
    git branch --merged HEAD 2>/dev/null | grep -v '^\*\|main\|master'
  else
    echo "No stale branches."
  fi
else
  echo "Not on main branch, skipping stale branch check."
fi