#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPENCODE_JSON="${PROJECT_ROOT}/opencode.json"
EXCLUDE_FILE="$(cd "$PROJECT_ROOT" && git rev-parse --git-path info/exclude 2>/dev/null || true)"
if [ -n "$EXCLUDE_FILE" ] && [ "${EXCLUDE_FILE#/}" = "$EXCLUDE_FILE" ]; then
    EXCLUDE_FILE="${PROJECT_ROOT}/${EXCLUDE_FILE}"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_err()  { echo -e "${RED}[ERR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_step() { echo -e "\n=== $1 ==="; }

log_step "Bootstrap rldyour-opencode agent-only context"

if [ ! -f "$OPENCODE_JSON" ]; then
    log_err "opencode.json not found at ${OPENCODE_JSON}"
    exit 1
fi
log_ok "opencode.json found"

log_step "Installing .git/info/exclude patterns"

EXCLUDE_PATTERNS=(
    "# rldyour-opencode agent-only files"
    "AGENTS.md"
    ".serena/"
    ".opencode/agents/"
    ".opencode/skills/"
    ".opencode/commands/"
    ".claude/"
    ".cursor/rules/"
    ".agents/"
    "REVIEW.md"
    "# end rldyour-opencode agent-only files"
)

if [ -z "$EXCLUDE_FILE" ]; then
    log_warn "Not inside a git worktree; skipping .git/info/exclude installation"
else
    if [ ! -f "$EXCLUDE_FILE" ]; then
        mkdir -p "$(dirname "$EXCLUDE_FILE")"
        touch "$EXCLUDE_FILE"
    fi

    RLDYOUR_BLOCK_FOUND=false
    if grep -q "rldyour-opencode agent-only files" "$EXCLUDE_FILE" 2>/dev/null; then
        RLDYOUR_BLOCK_FOUND=true
    fi

    if [ "$RLDYOUR_BLOCK_FOUND" = true ]; then
        log_ok "Exclude patterns already installed"
    else
        echo "" >> "$EXCLUDE_FILE"
        for pattern in "${EXCLUDE_PATTERNS[@]}"; do
            echo "$pattern" >> "$EXCLUDE_FILE"
        done
        log_ok "Exclude patterns installed in $EXCLUDE_FILE"
    fi
fi

log_step "Verifying agent-only directory structure"

for dir in ".opencode/agents" ".opencode/skills" ".opencode/commands" ".serena/memories"; do
    if [ -d "${PROJECT_ROOT}/${dir}" ]; then
        count=$(find "${PROJECT_ROOT}/${dir}" -type f 2>/dev/null | wc -l | tr -d ' ')
        log_ok "${dir}/ exists (${count} files)"
    else
        log_warn "${dir}/ not found"
    fi
done

log_step "Verifying references directory"

REFS_DIR="${PROJECT_ROOT}/references"
if [ -d "$REFS_DIR" ]; then
    count=$(find "$REFS_DIR" -type f -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
    log_ok "references/ exists (${count} reference files)"
else
    log_warn "references/ not found"
fi

log_step "Verifying MCP connectivity"

if [ ! -f "$OPENCODE_JSON" ]; then
    log_err "Cannot check MCP without opencode.json"
else
    python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    cfg = json.load(f)

mcp = cfg.get('mcp', {})
if not mcp:
    print('[WARN] No MCP servers configured')
    sys.exit(0)

for name, server in mcp.items():
    enabled = server.get('enabled', True)
    stype = server.get('type', 'unknown')
    if enabled:
        print(f'[OK] MCP server \"{name}\" ({stype}) enabled')
    else:
        print(f'[WARN] MCP server \"{name}\" ({stype}) disabled')
" "$OPENCODE_JSON"
fi

log_step "Verifying OpenCode version"

if command -v opencode &>/dev/null; then
    log_ok "opencode CLI found: $(opencode version 2>/dev/null || echo 'version unknown')"
else
    log_warn "opencode CLI not found on PATH"
fi

log_step "Bootstrap complete"

echo ""
echo "Agent-only files are excluded from normal branch history."
echo "Durable agent context is tracked on main; keep runtime-local files ignored."
echo ""
echo "Next steps:"
echo "  1. Run ./scripts/doctor_opencode.sh for full diagnostics"
echo "  2. Start OpenCode in the project directory"
echo "  3. Use /ry-init to initialize project context"
