#!/usr/bin/env bash
# rldyour flow post-task state computation
# Computes git, Serena, fullrepo, and instruction-docs state as JSON
set -euo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Git state
branch="$(git branch --show-current 2>/dev/null || echo 'HEAD')"
dirty_files="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
if [ "$dirty_files" -eq 0 ]; then
  git_dirty="false"
else
  git_dirty="true"
fi
ahead="$(git rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo '0')"
behind="$(git rev-list --count 'HEAD..@{upstream}' 2>/dev/null || echo '0')"
head_sha="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"

# Fullrepo state
fullrepo_exists="false"
if git branch -r 2>/dev/null | grep -q 'origin/fullrepo'; then
  fullrepo_exists="true"
fi

# Serena memory state
serena_current="unknown"
serena_mem_count=0
if [ -d "$root/.serena/memories" ]; then
  serena_mem_count="$(find "$root/.serena/memories" -name '*.md' | wc -l | tr -d ' ')"
  if [ -f "$root/.serena/.serena_sync_state.json" ]; then
    serena_current="stale"
  else
    serena_current="fresh"
  fi
fi

# Instruction docs state
agents_md_exists="false"
[ -f "$root/AGENTS.md" ] && agents_md_exists="true"

# Output JSON
cat <<EOF
{
  "git": {
    "branch": "$branch",
    "head_sha": "$head_sha",
    "dirty": $git_dirty,
    "dirty_files": $dirty_files,
    "ahead": $ahead,
    "behind": $behind
  },
  "fullrepo": {
    "exists": $fullrepo_exists
  },
  "serena": {
    "memories_current": "$serena_current",
    "memory_count": $serena_mem_count
  },
  "instruction_docs": {
    "agents_md": $agents_md_exists
  },
  "sync_needed": $([ "$git_dirty" = "true" ] || [ "$serena_current" = "stale" ] || [ "$ahead" -gt 0 ] && echo "true" || echo "false")
}
EOF