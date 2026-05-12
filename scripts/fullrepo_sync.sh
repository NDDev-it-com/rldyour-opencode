#!/usr/bin/env bash
set -euo pipefail

AGENT_ONLY_PATTERNS=(
  "AGENTS.md"
  ".opencode/"
  ".serena/"
  ".claude/"
  ".cursor/"
  ".agents/"
  ".windsurf/"
  ".aider"
  "docs/"
  "references/"
  "scripts/"
)

RUNTIME_EXCLUDE_PATTERNS=(
  ".serena/cache/"
  ".serena/project.local.yml"
  ".opencode/local.json"
  ".opencode/node_modules/"
  "browser/"
  "node_modules/"
)

FULLREPO_BRANCH="fullrepo"

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  bootstrap-init    Install .git/info/exclude patterns and restore from fullrepo
  restore           Restore agent-only files from origin/fullrepo
  publish           Publish current agent-only files to origin/fullrepo
  status            Show current sync status
  status-json       Show current sync status as JSON

Options:
  -h, --help        Show this help message
EOF
}

git_root() {
  git rev-parse --show-toplevel 2>/dev/null
}

current_branch() {
  git branch --show-current 2>/dev/null || echo "HEAD"
}

is_dirty() {
  [ -n "$(git status --porcelain 2>/dev/null)" ]
}

ahead_count() {
  local count
  count=$(git rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo "0")
  echo "$count"
}

behind_count() {
  local count
  count=$(git rev-list --count "HEAD..@{upstream}" 2>/dev/null || echo "0")
  echo "$count"
}

cmd_bootstrap_init() {
  local root
  root=$(git_root) || { echo "Error: not in a git repo" >&2; exit 1; }

  echo "[fullrepo] Installing git exclude patterns..."

  local exclude_file="$root/.git/info/exclude"
  mkdir -p "$(dirname "$exclude_file")"

  if [ -f "$exclude_file" ]; then
    if ! grep -q "# rldyour-opencode agent-only" "$exclude_file"; then
      echo "" >> "$exclude_file"
      echo "# rldyour-opencode agent-only" >> "$exclude_file"
      for pattern in "${AGENT_ONLY_PATTERNS[@]}"; do
        echo "$pattern" >> "$exclude_file"
      done
      echo "[fullrepo] Added exclude patterns to $exclude_file"
    else
      echo "[fullrepo] Exclude patterns already present"
    fi
  else
    echo "# rldyour-opencode agent-only" > "$exclude_file"
    for pattern in "${AGENT_ONLY_PATTERNS[@]}"; do
      echo "$pattern" >> "$exclude_file"
    done
    echo "[fullrepo] Created $exclude_file with exclude patterns"
  fi

  echo "[fullrepo] Checking fullrepo branch..."
  if git branch -r | grep -q "origin/$FULLREPO_BRANCH" 2>/dev/null; then
    echo "[fullrepo] Restoring agent-only files from origin/$FULLREPO_BRANCH..."
    cmd_restore
  else
    echo "[fullrepo] No origin/$FULLREPO_BRANCH found. Run 'publish' to create it."
  fi

  echo "[fullrepo] Bootstrap complete."
}

cmd_restore() {
  local root
  root=$(git_root) || { echo "Error: not in a git repo" >&2; exit 1; }

  if ! git branch -r | grep -q "origin/$FULLREPO_BRANCH" 2>/dev/null; then
    echo "[fullrepo] Error: origin/$FULLREPO_BRANCH does not exist" >&2
    exit 1
  fi

  echo "[fullrepo] Restoring agent-only files from origin/$FULLREPO_BRANCH..."

  local tmp_dir
  tmp_dir=$(mktemp -d)
  git worktree add "$tmp_dir" "origin/$FULLREPO_BRANCH" --detach 2>/dev/null

  for pattern in "${AGENT_ONLY_PATTERNS[@]}"; do
    if [ -e "$tmp_dir/$pattern" ]; then
      echo "  Restoring $pattern"
      cp -r "$tmp_dir/$pattern" "$root/" 2>/dev/null || true
    fi
  done

  git worktree remove "$tmp_dir" 2>/dev/null
  rm -rf "$tmp_dir"

  echo "[fullrepo] Restore complete."
}

cmd_publish() {
  local root
  root=$(git_root) || { echo "Error: not in a git repo" >&2; exit 1; }

  echo "[fullrepo] Publishing agent-only files to $FULLREPO_BRANCH..."

  local tmp_dir
  tmp_dir=$(mktemp -d)
  git worktree add "$tmp_dir" "origin/$FULLREPO_BRANCH" --detach 2>/dev/null || {
    echo "[fullrepo] Creating new $FULLREPO_BRANCH..."
    git checkout --orphan "$FULLREPO_BRANCH" 2>/dev/null
    git rm -rf . 2>/dev/null || true
    git commit --allow-empty -m "chore: initialize fullrepo branch" 2>/dev/null
    git checkout "$(current_branch)" 2>/dev/null
    git worktree add "$tmp_dir" "$FULLREPO_BRANCH" --detach 2>/dev/null
  }

  rm -rf "$tmp_dir"/*

  for pattern in "${AGENT_ONLY_PATTERNS[@]}"; do
    if [ -e "$root/$pattern" ]; then
      echo "  Adding $pattern"
      cp -r "$root/$pattern" "$tmp_dir/" 2>/dev/null || true
    fi
  done

  # Remove runtime artifacts from snapshot
  for rp in "${RUNTIME_EXCLUDE_PATTERNS[@]}"; do
    rm -rf "$tmp_dir/$rp" 2>/dev/null || true
  done

  # Secret detection
  local secrets_found=0
  while IFS= read -r line; do
    if echo "$line" | grep -qiE '(PRIVATE_KEY|SECRET_KEY|PASSWORD|TOKEN|API_KEY)\s*=\s*[^"]*\S'; then
      if ! echo "$line" | grep -qiE '(example|template|sample|placeholder|xxx|todo)'; then
        echo "[fullrepo] WARNING: Potential secret in $(echo "$line" | cut -d: -1)" >&2
        secrets_found=1
      fi
    fi
  done < <(cd "$tmp_dir" && grep -r --include='*.md' --include='*.json' --include='*.yml' --include='*.yaml' --include='*.ts' --include='*.sh' . 2>/dev/null || true)

  if [ "$secrets_found" -eq 1 ]; then
    echo "[fullrepo] ERROR: Secrets detected in agent-only content. Remove them before publishing." >&2
    git worktree remove "$tmp_dir" 2>/dev/null
    rm -rf "$tmp_dir"
    exit 1
  fi

  cd "$tmp_dir"
  git add -A 2>/dev/null
  if git diff --cached --quiet 2>/dev/null; then
    echo "[fullrepo] No changes to publish."
  else
    git commit -m "chore: sync fullrepo at $(date -u +%Y-%m-%dT%H:%M:%SZ)" 2>/dev/null
    git push origin "HEAD:refs/heads/$FULLREPO_BRANCH" --force-with-lease 2>/dev/null
    echo "[fullrepo] Published to origin/$FULLREPO_BRANCH."
  fi

  cd "$root"
  git worktree remove "$tmp_dir" 2>/dev/null
  rm -rf "$tmp_dir"
}

cmd_status() {
  local root
  root=$(git_root) || { echo "Not in a git repo" >&2; exit 1; }

  local branch
  branch=$(current_branch)
  local dirty="clean"
  is_dirty && dirty="dirty"
  local ahead
  ahead=$(ahead_count)
  local behind
  behind=$(behind_count)

  echo "Branch: $branch"
  echo "Working tree: $dirty"
  echo "Ahead: $ahead  Behind: $behind"

  local fullrepo_exists="no"
  git branch -r | grep -q "origin/$FULLREPO_BRANCH" 2>/dev/null && fullrepo_exists="yes"
  echo "Fullrepo branch: $fullrepo_exists"

  local serena_fresh="unknown"
  if [ -d "$root/.serena/memories" ]; then
    local mem_count
    mem_count=$(find "$root/.serena/memories" -name "*.md" | wc -l | tr -d ' ')
    echo "Serena memories: $mem_count files"
  else
    echo "Serena memories: none"
  fi
}

cmd_status_json() {
  local root
  root=$(git_root) || { echo '{"error":"not in a git repo"}' >&2; exit 1; }

  local branch dirty ahead behind fullrepo_exists mem_count
  branch=$(current_branch)
  is_dirty && dirty="dirty" || dirty="clean"
  ahead=$(ahead_count)
  behind=$(behind_count)
  git branch -r | grep -q "origin/$FULLREPO_BRANCH" 2>/dev/null && fullrepo_exists="true" || fullrepo_exists="false"
  mem_count=$(find "$root/.serena/memories" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

  cat <<EOF
{
  "branch": "$branch",
  "dirty": "$dirty",
  "ahead": $ahead,
  "behind": $behind,
  "fullrepo_exists": $fullrepo_exists,
  "serena_memory_count": $mem_count
}
EOF
}

case "${1:-}" in
  bootstrap-init) cmd_bootstrap_init ;;
  restore) cmd_restore ;;
  publish) cmd_publish ;;
  status) cmd_status ;;
  status-json) cmd_status_json ;;
  -h|--help|help) usage ;;
  *) usage; exit 1 ;;
esac