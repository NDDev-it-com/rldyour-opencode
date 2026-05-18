#!/usr/bin/env bash
set -euo pipefail

AGENT_ONLY_PATTERNS=(
  "AGENTS.md"
  ".serena/"
  ".claude/"
  ".cursor/"
  ".agents/"
  ".windsurf/"
  ".aider"
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
EXCLUDE_START_MARKER="# >>> rldyour fullrepo agent-only files >>>"
EXCLUDE_END_MARKER="# <<< rldyour fullrepo agent-only files <<<"

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  install-exclude   Install .git/info/exclude patterns only
  bootstrap-init    Install .git/info/exclude patterns and restore from fullrepo
  restore           Restore agent-only files from origin/fullrepo
  publish           Publish current agent-only files to origin/fullrepo
  status            Show current sync status
  status-json       Show current sync status as JSON

Options:
  -h, --help        Show this help message
EOF
}

git_identity_env() {
  export GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-rldyour-opencode}"
  export GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-rldyour-opencode@example.invalid}"
  export GIT_COMMITTER_NAME="${GIT_COMMITTER_NAME:-rldyour-opencode}"
  export GIT_COMMITTER_EMAIL="${GIT_COMMITTER_EMAIL:-rldyour-opencode@example.invalid}"
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

install_exclude_patterns() {
  local root
  root=$(git_root) || { echo "Error: not in a git repo" >&2; exit 1; }

  echo "[fullrepo] Installing git exclude patterns..."

  local exclude_file="$root/.git/info/exclude"
  mkdir -p "$(dirname "$exclude_file")"

  local block
  block="$EXCLUDE_START_MARKER"$'\n'
  for pattern in "${AGENT_ONLY_PATTERNS[@]}"; do
    block+="$pattern"$'\n'
  done
  block+="$EXCLUDE_END_MARKER"$'\n'

  if [ -f "$exclude_file" ] && grep -qF "$EXCLUDE_START_MARKER" "$exclude_file"; then
    python3 - "$exclude_file" "$EXCLUDE_START_MARKER" "$EXCLUDE_END_MARKER" "$block" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
start = sys.argv[2]
end = sys.argv[3]
block = sys.argv[4]
text = path.read_text(encoding="utf-8")
start_index = text.index(start)
end_index = text.index(end, start_index) + len(end)
if end_index < len(text) and text[end_index:end_index + 1] == "\n":
    end_index += 1
path.write_text(text[:start_index] + block + text[end_index:], encoding="utf-8")
PY
    echo "[fullrepo] Refreshed exclude patterns in $exclude_file"
  elif [ -f "$exclude_file" ]; then
    printf '\n%s' "$block" >> "$exclude_file"
    echo "[fullrepo] Added exclude patterns to $exclude_file"
  else
    printf '%s' "$block" > "$exclude_file"
    echo "[fullrepo] Created $exclude_file with exclude patterns"
  fi

  python3 - "$exclude_file" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
new_text = re.sub(
    r"\n?# rldyour-opencode agent-only\n(?:(?:AGENTS\.md|\.opencode/|\.serena/|\.claude/|\.cursor/|\.agents/|\.windsurf/|\.aider|docs/|references/|scripts/)\n)+",
    "\n",
    text,
)
if new_text != text:
    path.write_text(new_text, encoding="utf-8")
PY
}

cmd_install_exclude() {
  install_exclude_patterns
}

cmd_bootstrap_init() {
  install_exclude_patterns

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
  # Reviewer wave 2026-05-18 quality F-5 / S-2 closure: cmd_restore had no
  # EXIT trap, so a failure between `mktemp -d` and the explicit cleanup
  # would orphan the temp dir plus its worktree registration. Mirror the
  # cmd_publish trap pattern so set -e exits cannot strand artefacts.
  trap '_restore_cleanup "${tmp_dir:-}"' EXIT
  git worktree add "$tmp_dir" "origin/$FULLREPO_BRANCH" --detach 2>/dev/null

  for pattern in "${AGENT_ONLY_PATTERNS[@]}"; do
    if [ -e "$tmp_dir/$pattern" ]; then
      echo "  Restoring $pattern"
      cp -r "$tmp_dir/$pattern" "$root/" 2>/dev/null || true
    fi
  done

  # Explicit success-path cleanup (mirrors cmd_publish pattern; EXIT trap
  # remains as the failure-path safety net).
  _restore_cleanup "$tmp_dir"
  trap - EXIT

  echo "[fullrepo] Restore complete."
}

_restore_cleanup() {
  # Defensive: every arg may be empty under `set -u` if the trap fires
  # before its variables were bound (e.g. mktemp failed).
  local tmp_dir="${1:-}"
  if [ -n "$tmp_dir" ] && [ -d "$tmp_dir" ]; then
    # Best-effort worktree de-registration. `git worktree remove --force`
    # is idempotent enough: it errors loudly if `$tmp_dir` was never a
    # registered worktree, but we suppress that — the rm -rf below catches
    # the dangling tmp dir regardless.
    if command -v git >/dev/null 2>&1; then
      git worktree remove --force "$tmp_dir" 2>/dev/null || true
    fi
    rm -rf "$tmp_dir"
  fi
}

cmd_publish() {
  local root original_branch
  root=$(git_root) || { echo "Error: not in a git repo" >&2; exit 1; }
  original_branch=$(current_branch)

  if [ "$original_branch" = "HEAD" ] || [ -z "$original_branch" ]; then
    echo "[fullrepo] Error: must run publish from a named branch (current is detached)" >&2
    exit 1
  fi

  install_exclude_patterns

  if is_dirty; then
    echo "[fullrepo] Error: refusing to publish while non-runtime tracked/untracked files are dirty" >&2
    git status --short >&2
    exit 1
  fi

  echo "[fullrepo] Publishing complete snapshot to $FULLREPO_BRANCH (HEAD + agent-only files, from $original_branch)..."

  local tmp_dir
  tmp_dir=$(mktemp -d)

  # Always use a temporary worktree so the main worktree is never touched.
  # Cleanup is registered with trap so we never leave the main checkout
  # stranded on a half-built orphan branch.
  trap '_publish_cleanup "${tmp_dir:-}" "${root:-}" "${original_branch:-}"' EXIT

  # Start from the normal branch tree. `fullrepo` is a generated portable
  # snapshot: current HEAD plus ignored agent-only context. Starting from HEAD
  # keeps runtime files (`opencode.json`, VERSION, workflows, governance docs)
  # present in the snapshot and matches the generic rldyour-flow state model.
  git worktree add --detach "$tmp_dir" HEAD >/dev/null 2>&1

  # Overlay agent-only patterns from the main worktree. Strip trailing slash so
  # cp -r preserves the directory name itself (cp "$root/.serena/" "$tmp/"
  # flattens contents; cp "$root/.serena" "$tmp/" produces "$tmp/.serena/").
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

    local snapshot_tree expected_remote remote_tree commit
    snapshot_tree=$(git write-tree)
    expected_remote=$(git ls-remote --heads origin "$FULLREPO_BRANCH" 2>/dev/null | awk '{print $1}' || true)
    remote_tree=""
    if [ -n "$expected_remote" ]; then
      git fetch --quiet origin "+refs/heads/$FULLREPO_BRANCH:refs/remotes/origin/$FULLREPO_BRANCH" 2>/dev/null || true
      remote_tree=$(git rev-parse --verify --quiet "refs/remotes/origin/$FULLREPO_BRANCH^{tree}" || true)
    fi

    if [ -n "$remote_tree" ] && [ "$remote_tree" = "$snapshot_tree" ]; then
      git update-ref "refs/heads/$FULLREPO_BRANCH" "$expected_remote"
      echo "[fullrepo] No changes to publish."
    else
      local parent_args=()
      if [ -n "$expected_remote" ]; then
        parent_args=(-p "$expected_remote")
      else
        parent_args=(-p "$(git -C "$root" rev-parse HEAD)")
      fi
      git_identity_env
      commit=$(git commit-tree "$snapshot_tree" "${parent_args[@]}" -m "chore: sync fullrepo at $(date -u +%Y-%m-%dT%H:%M:%SZ)")
      git update-ref "refs/heads/$FULLREPO_BRANCH" "$commit"

      local lease_args=()
      if [ -n "$expected_remote" ]; then
        lease_args=("--force-with-lease=refs/heads/$FULLREPO_BRANCH:$expected_remote")
      else
        lease_args=("--force-with-lease=refs/heads/$FULLREPO_BRANCH")
      fi
      if git push "${lease_args[@]}" origin "$commit:refs/heads/$FULLREPO_BRANCH" 2>&1; then
        git update-ref "refs/remotes/origin/$FULLREPO_BRANCH" "$commit" 2>/dev/null || true
        echo "[fullrepo] Published to origin/$FULLREPO_BRANCH."
      else
        echo "[fullrepo] Push failed — see error above." >&2
        exit 1
      fi
    fi
  )

  # Clean the staging worktree immediately on the success path. The EXIT trap
  # remains as the failure-path safety net, but relying only on process EXIT
  # left detached /tmp worktrees behind in live 0.11.4 release verification.
  _publish_cleanup "$tmp_dir" "$root" "$original_branch"
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

expected_fullrepo_tree() {
  local root tmp_index
  root=$(git_root) || { echo ""; return 1; }
  tmp_index=$(mktemp)

  GIT_INDEX_FILE="$tmp_index" git -C "$root" read-tree HEAD
  for pattern in "${AGENT_ONLY_PATTERNS[@]}"; do
    local clean="${pattern%/}"
    if [ -e "$root/$clean" ]; then
      GIT_INDEX_FILE="$tmp_index" git -C "$root" add -f -- "$clean" 2>/dev/null || true
    fi
  done

  for rp in "${RUNTIME_EXCLUDE_PATTERNS[@]}"; do
    local clean="${rp%/}"
    if [ -n "$clean" ]; then
      GIT_INDEX_FILE="$tmp_index" git -C "$root" rm --cached -r -q --ignore-unmatch -- "$clean" 2>/dev/null || true
    fi
  done

  local indexed_path base_name
  while IFS= read -r -d '' indexed_path; do
    base_name=$(basename "$indexed_path")
    for name in "${RUNTIME_EXCLUDE_DIRNAMES[@]}"; do
      if [[ "$indexed_path" == "$name/"* || "$indexed_path" == */"$name"/* || "$base_name" == "$name" ]]; then
        GIT_INDEX_FILE="$tmp_index" git -C "$root" rm --cached -r -q --ignore-unmatch -- "$indexed_path" 2>/dev/null || true
        continue 2
      fi
    done
    case "$indexed_path" in
      *.pyc|*.pyo)
        GIT_INDEX_FILE="$tmp_index" git -C "$root" rm --cached -q --ignore-unmatch -- "$indexed_path" 2>/dev/null || true
        ;;
    esac
  done < <(GIT_INDEX_FILE="$tmp_index" git -C "$root" ls-files -z)

  local tree
  tree=$(GIT_INDEX_FILE="$tmp_index" git -C "$root" write-tree)

  rm -f "$tmp_index"
  echo "$tree"
}

cmd_status_json() {
  local root
  root=$(git_root) || { echo '{"error":"not in a git repo"}' >&2; exit 1; }

  local branch dirty ahead behind fullrepo_local fullrepo_remote mem_count
  local expected_tree local_tree remote_tree remote_sha local_sha
  branch=$(current_branch)
  is_dirty && dirty="dirty" || dirty="clean"
  ahead=$(ahead_count)
  behind=$(behind_count)
  git show-ref --verify --quiet "refs/heads/$FULLREPO_BRANCH" && fullrepo_local="true" || fullrepo_local="false"
  git branch -r 2>/dev/null | grep -q "origin/$FULLREPO_BRANCH" && fullrepo_remote="true" || fullrepo_remote="false"
  expected_tree=$(expected_fullrepo_tree)
  local_sha=$(git rev-parse --verify --quiet "refs/heads/$FULLREPO_BRANCH^{commit}" 2>/dev/null || true)
  local_tree=$(git rev-parse --verify --quiet "refs/heads/$FULLREPO_BRANCH^{tree}" 2>/dev/null || true)
  remote_sha=$(git rev-parse --verify --quiet "refs/remotes/origin/$FULLREPO_BRANCH^{commit}" 2>/dev/null || true)
  remote_tree=$(git rev-parse --verify --quiet "refs/remotes/origin/$FULLREPO_BRANCH^{tree}" 2>/dev/null || true)
  if [ -d "$root/.serena/memories" ]; then
    mem_count=$(find "$root/.serena/memories" -name "*.md" | wc -l | tr -d ' ')
  else
    mem_count="0"
  fi

  # JSON-escape via Python so a branch name containing `"`, `\`, or any
  # control char cannot produce malformed output. Booleans and integers
  # are passed via env to keep the shell -> Python boundary explicit.
  BRANCH="$branch" DIRTY="$dirty" \
  AHEAD="$ahead" BEHIND="$behind" \
  FL="$fullrepo_local" FR="$fullrepo_remote" \
  MEM="$mem_count" EXPECTED_TREE="$expected_tree" \
  LOCAL_SHA="$local_sha" LOCAL_TREE="$local_tree" \
  REMOTE_SHA="$remote_sha" REMOTE_TREE="$remote_tree" \
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
    "expected_fullrepo_tree": os.environ["EXPECTED_TREE"],
    "local_fullrepo_sha": os.environ["LOCAL_SHA"][:12],
    "remote_fullrepo_sha": os.environ["REMOTE_SHA"][:12],
    "local_fullrepo_matches_worktree": bool(os.environ["LOCAL_TREE"] and os.environ["LOCAL_TREE"] == os.environ["EXPECTED_TREE"]),
    "remote_fullrepo_matches_worktree": bool(os.environ["REMOTE_TREE"] and os.environ["REMOTE_TREE"] == os.environ["EXPECTED_TREE"]),
}, indent=2))
'
}

case "${1:-}" in
  install-exclude) cmd_install_exclude ;;
  bootstrap-init) cmd_bootstrap_init ;;
  restore) cmd_restore ;;
  publish) cmd_publish ;;
  status) cmd_status ;;
  status-json) cmd_status_json ;;
  -h|--help|help) usage ;;
  *) usage; exit 1 ;;
esac
