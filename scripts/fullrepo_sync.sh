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
  ".serena/.flow_sync_marker"
  ".serena/.flow_post_task_state.json"
  ".serena/.sync_marker"
  ".serena/.serena_sync_state.json"
  ".serena/.auto_sync_head"
  ".serena/.active_workflow_intent.json"
  ".serena/.dirty_stop_ack"
  ".serena/.gitignore"
  ".serena/.command_audit.log"
  ".opencode/local.json"
  ".opencode/node_modules/"
  "browser/"
  "node_modules/"
)

# Directory-name globs stripped recursively after the per-path removals
# above. Catches caches that may appear anywhere in the agent-only tree.
RUNTIME_EXCLUDE_DIRNAMES=(
  "__pycache__"
  ".pytest_cache"
  ".cache"
  ".venv"
  "node_modules"
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
  # Whitelisted runtime markers must not flip the working tree to "dirty";
  # they are regenerated every session and never committed.
  local marker_re='\.serena/\.(flow_(sync_marker|post_task_state\.json)|sync_marker|serena_sync_state\.json|auto_sync_head|active_workflow_intent\.json|dirty_stop_ack|gitignore)$'
  git status --porcelain 2>/dev/null | grep -vqE "$marker_re"
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
  local root original_branch
  root=$(git_root) || { echo "Error: not in a git repo" >&2; exit 1; }
  original_branch=$(current_branch)

  if [ "$original_branch" = "HEAD" ] || [ -z "$original_branch" ]; then
    echo "[fullrepo] Error: must run publish from a named branch (current is detached)" >&2
    exit 1
  fi

  echo "[fullrepo] Publishing agent-only files to $FULLREPO_BRANCH (from $original_branch)..."

  local tmp_dir
  tmp_dir=$(mktemp -d)

  # Always use a temporary worktree so the main worktree is never touched.
  # Cleanup is registered with trap so we never leave the main checkout
  # stranded on a half-built orphan branch.
  trap '_publish_cleanup "${tmp_dir:-}" "${root:-}" "${original_branch:-}"' EXIT

  if git ls-remote --exit-code origin "$FULLREPO_BRANCH" >/dev/null 2>&1; then
    # Remote orphan exists — start from its tip
    git worktree add "$tmp_dir" "origin/$FULLREPO_BRANCH" --detach 2>/dev/null
  else
    echo "[fullrepo] No origin/$FULLREPO_BRANCH yet — creating empty orphan in temp worktree"
    # Use detached HEAD in a tmp worktree, then make it a new orphan branch.
    # This NEVER touches main worktree's HEAD.
    git worktree add --detach "$tmp_dir" HEAD 2>/dev/null
    (
      cd "$tmp_dir"
      git checkout --orphan "_fullrepo_init" >/dev/null 2>&1
      git rm -rf . >/dev/null 2>&1 || true
    )
  fi

  # Wipe tmp worktree contents (including hidden, but never the .git pointer)
  find "$tmp_dir" -mindepth 1 -maxdepth 1 ! -name ".git" -exec rm -rf {} +

  # Copy agent-only patterns. Strip trailing slash so cp -r preserves the
  # directory name itself (cp "$root/.serena/" "$tmp/" flattens contents;
  # cp "$root/.serena" "$tmp/" produces "$tmp/.serena/").
  for pattern in "${AGENT_ONLY_PATTERNS[@]}"; do
    local clean="${pattern%/}"
    if [ -e "$root/$clean" ]; then
      echo "  Adding $clean"
      cp -r "$root/$clean" "$tmp_dir/" 2>/dev/null || true
    fi
  done

  # Remove runtime artefacts by path (per-entry). Guard against an empty
  # pattern which would otherwise expand to `rm -rf "$tmp_dir/"` and wipe
  # the entire staging area.
  for rp in "${RUNTIME_EXCLUDE_PATTERNS[@]}"; do
    local clean="${rp%/}"
    if [ -n "$clean" ]; then
      rm -rf "${tmp_dir:?}/$clean" 2>/dev/null || true
    fi
  done

  # Remove runtime artefacts by directory name (anywhere in tree)
  for name in "${RUNTIME_EXCLUDE_DIRNAMES[@]}"; do
    find "$tmp_dir" -depth -name "$name" -type d -exec rm -rf {} + 2>/dev/null || true
  done

  # Also strip Python bytecode files anywhere
  find "$tmp_dir" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

  # Secret detection. `grep -rI` follows binary-skip heuristic + reads every
  # text file regardless of extension, closing the previous coverage gap
  # (`--include='*.md|*.json|*.yml|*.yaml|*.ts|*.sh'` missed `*.py`, `*.log`,
  # and extension-less files like `LICENSE` / `CODEOWNERS` / `VERSION`).
  local secrets_found=0
  while IFS= read -r line; do
    if echo "$line" | grep -qiE '(PRIVATE_KEY|SECRET_KEY|PASSWORD|TOKEN|API_KEY)\s*=\s*[^"]*\S'; then
      if ! echo "$line" | grep -qiE '(example|template|sample|placeholder|xxx|todo|YOUR_|<redacted-)'; then
        echo "[fullrepo] WARNING: Potential secret in $(echo "$line" | cut -d: -f1)" >&2
        secrets_found=1
      fi
    fi
  done < <(cd "$tmp_dir" && grep -rIE '(PRIVATE_KEY|SECRET_KEY|PASSWORD|TOKEN|API_KEY)' . 2>/dev/null || true)

  if [ "$secrets_found" -eq 1 ]; then
    echo "[fullrepo] ERROR: Secrets detected in agent-only content. Remove them before publishing." >&2
    exit 1
  fi

  (
    cd "$tmp_dir"
    # CRITICAL: use `git add -f` because the tmp worktree shares the parent
    # repo's `.git/`, and that repo's `.git/info/exclude` block ignores the
    # exact agent-only paths we are trying to publish (AGENTS.md, .serena/,
    # .claude/, …). Without `-f` those files are silently skipped, leaving
    # only `.opencode/`, `docs/`, `references/`, `scripts/` in the pushed
    # tree — verified failure mode on the first publish attempt.
    git add -f -A 2>/dev/null
    if git diff --cached --quiet 2>/dev/null; then
      echo "[fullrepo] No changes to publish."
    else
      git commit -m "chore: sync fullrepo at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1
      if git push origin "HEAD:refs/heads/$FULLREPO_BRANCH" --force-with-lease 2>&1; then
        echo "[fullrepo] Published to origin/$FULLREPO_BRANCH."
      else
        echo "[fullrepo] Push failed — see error above." >&2
        exit 1
      fi
    fi
  )
}

_publish_cleanup() {
  # Defensive: every arg may be empty under `set -u` if the trap fires
  # before its variables were bound (e.g. mktemp failed).
  local tmp_dir="${1:-}" root="${2:-}" original_branch="${3:-}"

  # Restore main worktree to the original named branch if a stale half-publish
  # ever left us on an orphan ref (defensive — the new cmd_publish flow uses
  # only the tmp worktree, but old half-completed runs may still need this).
  if [ -n "$root" ] && [ -d "$root" ]; then
    cd "$root" 2>/dev/null || true
    local now
    now=$(git branch --show-current 2>/dev/null || echo "")
    if [ -n "$original_branch" ] && [ "$now" != "$original_branch" ]; then
      git checkout "$original_branch" >/dev/null 2>&1 || true
    fi
  fi
  if [ -n "$tmp_dir" ] && [ -d "$tmp_dir" ]; then
    git worktree remove --force "$tmp_dir" >/dev/null 2>&1 || true
    rm -rf "$tmp_dir" 2>/dev/null || true
  fi
  trap - EXIT
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

  local fullrepo_local="no" fullrepo_remote="no"
  git show-ref --verify --quiet "refs/heads/$FULLREPO_BRANCH" && fullrepo_local="yes"
  git branch -r 2>/dev/null | grep -q "origin/$FULLREPO_BRANCH" && fullrepo_remote="yes"
  echo "Fullrepo branch: local=$fullrepo_local remote=$fullrepo_remote"

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

  local branch dirty ahead behind fullrepo_local fullrepo_remote mem_count
  branch=$(current_branch)
  is_dirty && dirty="dirty" || dirty="clean"
  ahead=$(ahead_count)
  behind=$(behind_count)
  git show-ref --verify --quiet "refs/heads/$FULLREPO_BRANCH" && fullrepo_local="true" || fullrepo_local="false"
  git branch -r 2>/dev/null | grep -q "origin/$FULLREPO_BRANCH" && fullrepo_remote="true" || fullrepo_remote="false"
  mem_count=$(find "$root/.serena/memories" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

  # JSON-escape via Python so a branch name containing `"`, `\`, or any
  # control char cannot produce malformed output. Booleans and integers
  # are passed via env to keep the shell -> Python boundary explicit.
  BRANCH="$branch" DIRTY="$dirty" \
  AHEAD="$ahead" BEHIND="$behind" \
  FL="$fullrepo_local" FR="$fullrepo_remote" \
  MEM="$mem_count" \
  python3 -c '
import json, os
print(json.dumps({
    "branch": os.environ["BRANCH"],
    "dirty": os.environ["DIRTY"],
    "ahead": int(os.environ["AHEAD"]),
    "behind": int(os.environ["BEHIND"]),
    "fullrepo_local": os.environ["FL"] == "true",
    "fullrepo_remote": os.environ["FR"] == "true",
    "serena_memory_count": int(os.environ["MEM"]),
}, indent=2))
'
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