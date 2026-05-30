#!/usr/bin/env bash
# rldyour-opencode diagnostic bundle.
#
# Collects a timestamped directory under diagnostics/ with enough state
# for failure triage without leaking secrets. Intended for owner-driven
# bug reports and CI artifact upload. The diagnostics/ directory is
# git-ignored (see .gitignore — added in commit b30a7b5 etc.).
#
# Usage:
#   bash scripts/collect_diagnostics.sh                   # minimal bundle
#   bash scripts/collect_diagnostics.sh --include-doctor   # add LSP doctor
#   bash scripts/collect_diagnostics.sh --include-live-mcp # add live MCP probe
#   bash scripts/collect_diagnostics.sh --output PATH      # custom output dir

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${PROJECT_ROOT}"

INCLUDE_DOCTOR=0
INCLUDE_LIVE_MCP=0
OUT_BASE="${PROJECT_ROOT}/diagnostics"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --include-doctor) INCLUDE_DOCTOR=1; shift ;;
    --include-live-mcp) INCLUDE_LIVE_MCP=1; shift ;;
    --output) OUT_BASE="$2"; shift 2 ;;
    --help|-h)
      grep -E "^# " "$0" | sed -E 's/^# ?//' | head -10
      exit 0
      ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

STAMP=$(date -u +"%Y%m%dT%H%M%SZ")
BUNDLE="${OUT_BASE}/${STAMP}"
mkdir -p "${BUNDLE}"

log() { echo "[collect] $*" >&2; }

SANITIZER="${PROJECT_ROOT}/scripts/_sanitize_diag.py"

# Strip credential-shaped substrings from a file in place. Best-effort:
# missing sanitizer or python3 just logs a warning and leaves the file
# as-is — better to have a triage bundle with secrets visible to the
# owner than no bundle at all when collecting on a fresh checkout.
sanitize_file() {
  local target="$1"
  [ -f "${target}" ] || return 0
  if [ ! -f "${SANITIZER}" ]; then
    log "WARN sanitizer missing at ${SANITIZER}; ${target} not redacted"
    return 0
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    log "WARN python3 not on PATH; ${target} not redacted"
    return 0
  fi
  python3 "${SANITIZER}" "${target}" --in-place 2>/dev/null \
    || log "WARN sanitizer failed on ${target}; left as-is"
}

# Helper: run a command and tee stdout+stderr into a file, never fail.
# Output file is sanitised before return so secrets never persist.
run_cmd() {
  local name="$1"; shift
  local out="${BUNDLE}/${name}"
  log "${name}"
  if "$@" >"${out}" 2>&1; then
    sanitize_file "${out}"
    return 0
  else
    echo "[collect] command exited non-zero: $*" >>"${out}"
    sanitize_file "${out}"
    return 0
  fi
}

# Git state (no working-tree contents, only metadata).
run_cmd git-status.txt        git status -sb
run_cmd git-log.txt           git log --oneline -30
run_cmd git-remote.txt        git remote -v
run_cmd git-worktrees.txt     git worktree list

# Project version + manifests. opencode.json itself contains only env-var
# *references* (`{env:NAME}`) so it is safe to copy verbatim — `opencode debug
# config` is the surface where real tokens get substituted, and that path
# is routed through sanitize_file via run_cmd below.
cp -f VERSION       "${BUNDLE}/VERSION"          2>/dev/null || true
cp -f CHANGELOG.md  "${BUNDLE}/CHANGELOG.md"     2>/dev/null || true
cp -f opencode.json "${BUNDLE}/opencode.json"    2>/dev/null || true

# Validator + tests.
run_cmd validate.log          bash scripts/validate_config.sh
run_cmd deps-pins.json        bash scripts/check_deps_freshness.sh --json
run_cmd action-pins.txt       python3 scripts/check_action_pins.py .github/workflows
run_cmd flow-state.json       bash scripts/flow_post_task_state.sh
run_cmd git-audit.txt         bash scripts/git_sync_audit.sh
run_cmd fullrepo-status.json  bash scripts/fullrepo_sync.sh status-json
run_cmd mcp-smoke.json        python3 scripts/smoke_mcp_capabilities.py --mode static --json

if [ "${INCLUDE_LIVE_MCP}" -eq 1 ]; then
  run_cmd mcp-smoke-live.json python3 scripts/smoke_mcp_capabilities.py --mode all --json
fi

# OpenCode CLI state (skipped silently if not on PATH).
if command -v opencode >/dev/null 2>&1; then
  run_cmd opencode-info.txt   env NPM_CONFIG_PACKAGE_LOCK=false npm_config_package_lock=false opencode debug info
  run_cmd opencode-config.txt env NPM_CONFIG_PACKAGE_LOCK=false npm_config_package_lock=false opencode debug config
else
  echo "opencode CLI not on PATH; skipped" >"${BUNDLE}/opencode-cli.txt"
fi

# Optional LSP doctor pass.
if [ "${INCLUDE_DOCTOR}" -eq 1 ]; then
  run_cmd lsp-health.txt      bash scripts/check_lsps.sh
  run_cmd doctor.txt          bash scripts/doctor_opencode.sh
fi

# Environment fingerprint (no secrets).
{
  echo "uname=$(uname -a)"
  echo "shell=${SHELL:-unknown}"
  for bin in opencode bun bunx uvx python3 node git; do
    if command -v "$bin" >/dev/null 2>&1; then
      echo "${bin}_path=$(command -v "$bin")"
      "$bin" --version 2>/dev/null | head -1 | awk -v k="$bin" '{print k"_version="$0}'
    fi
  done
} >"${BUNDLE}/env.txt" 2>/dev/null

log "bundle ready: ${BUNDLE}"
echo "${BUNDLE}"
