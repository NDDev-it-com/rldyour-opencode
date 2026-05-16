#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPENCODE_JSON="${PROJECT_ROOT}/opencode.json"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ISSUES=0

log_ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
log_err()  { echo -e "  ${RED}[ERR]${NC} $1"; ISSUES=$((ISSUES + 1)); }
log_warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
log_info() { echo -e "  ${CYAN}[INFO]${NC} $1"; }

echo "========================================"
echo " rldyour-opencode Doctor"
echo "========================================"
echo ""

echo "=== Configuration File ==="
if [ -f "$OPENCODE_JSON" ]; then
    log_ok "opencode.json found"
    if python3 -c "import json, sys; json.load(open(sys.argv[1]))" "$OPENCODE_JSON" 2>/dev/null; then
        log_ok "opencode.json is valid JSON"
    else
        log_err "opencode.json has JSON syntax errors"
    fi

    model=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1])).get('model',''))" "$OPENCODE_JSON" 2>/dev/null)
    if [ -n "$model" ]; then
        log_info "Primary model: ${model}"
    fi

    small_model=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1])).get('small_model',''))" "$OPENCODE_JSON" 2>/dev/null)
    if [ -n "$small_model" ]; then
        log_info "Small model: ${small_model}"
    fi

    # OpenCode v1.14.x/v1.15.x accepts `"lsp"` as boolean `true` (enable all
    # built-ins) OR an object with per-server overrides (which also enables
    # built-ins + the custom map). Treat both as "enabled". Print the number
    # of custom servers when the object form is used so operators see the
    # current LSP catalog size at a glance.
    lsp_state=$(python3 -c "
import json, sys
cfg = json.load(open(sys.argv[1]))
lsp = cfg.get('lsp')
if lsp is True:
    print('enabled-default')
elif isinstance(lsp, dict):
    print(f'enabled-custom:{len(lsp)}')
elif lsp is False or lsp is None:
    print('disabled')
else:
    print(f'unknown:{type(lsp).__name__}')
" "$OPENCODE_JSON" 2>/dev/null || echo "parse-error")
    case "$lsp_state" in
        enabled-default)
            log_ok "LSP enabled (built-ins only)"
            ;;
        enabled-custom:*)
            log_ok "LSP enabled (${lsp_state#enabled-custom:} custom server(s) on top of built-ins)"
            ;;
        disabled)
            log_warn "LSP disabled"
            ;;
        *)
            log_warn "LSP config not recognized: ${lsp_state}"
            ;;
    esac
else
    log_err "opencode.json not found"
fi

echo ""
echo "=== AGENTS.md ==="
AGENTS_MD="${PROJECT_ROOT}/AGENTS.md"
if [ -f "$AGENTS_MD" ]; then
    lines=$(wc -l < "$AGENTS_MD" | tr -d ' ')
    log_ok "AGENTS.md found (${lines} lines)"
else
    log_warn "AGENTS.md not found"
fi

echo ""
echo "=== MCP Servers ==="
if [ -f "$OPENCODE_JSON" ]; then
    python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    cfg = json.load(f)

mcp = cfg.get('mcp', {})
if not mcp:
    print('  [WARN] No MCP servers configured')
    sys.exit(0)

for name, server in mcp.items():
    enabled = server.get('enabled', True)
    stype = server.get('type', 'unknown')
    status = 'enabled' if enabled else 'disabled'
    if stype == 'local':
        cmd = ' '.join(server.get('command', []))
        print(f'  [OK] {name}: {stype}, {status}, cmd={cmd[:60]}')
    elif stype == 'remote':
        url = server.get('url', 'N/A')
        print(f'  [OK] {name}: {stype}, {status}, url={url[:60]}')
    else:
        print(f'  [INFO] {name}: type={stype}, {status}')
" "$OPENCODE_JSON"
else
    log_warn "Cannot check MCP without opencode.json"
fi

echo ""
echo "=== LSP Status ==="
lsp_tools=(
    "pyright-langserver"
    "typescript-language-server"
    "rust-analyzer"
    "gopls"
    "clangd"
    "yaml-language-server"
    "bash-language-server"
    "taplo"
    "marksman"
    "docker-language-server"
    "ruff"
    "shellcheck"
)

for tool in "${lsp_tools[@]}"; do
    if command -v "$tool" &>/dev/null; then
        version_output=$("$tool" --version 2>/dev/null | head -1 || echo "unknown")
        log_ok "${tool}: ${version_output}"
    else
        log_warn "${tool}: not found on PATH"
    fi
done

echo ""
echo "=== Agent Discovery ==="
AGENTS_DIR="${PROJECT_ROOT}/.opencode/agents"
if [ -d "$AGENTS_DIR" ]; then
    count=0
    for f in "$AGENTS_DIR"/*.md; do
        [ -f "$f" ] || continue
        name=$(basename "$f" .md)
        if ! desc=$(python3 -c "
import re, sys
with open(sys.argv[1]) as fh:
    content = fh.read()
m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
if m:
    fm = m.group(1)
    dm = re.search(r'^description:\s*[\"\\']?(.+?)[\"\\']?\s*$', fm, re.MULTILINE)
    if dm:
        print(dm.group(1)[:80])
    else:
        print('(no description)')
else:
    print('(no frontmatter)')
" "$f" 2>/dev/null); then
            desc="(parse error)"
        fi
        log_info "Agent: ${name} — ${desc}"
        count=$((count + 1))
    done
    log_ok "Found ${count} agent(s)"
else
    log_warn "No agents directory"
fi

echo ""
echo "=== Skill Discovery ==="
SKILLS_DIR="${PROJECT_ROOT}/.opencode/skills"
if [ -d "$SKILLS_DIR" ]; then
    count=0
    for d in "$SKILLS_DIR"/*/; do
        [ -d "$d" ] || continue
        name=$(basename "$d")
        skill_md="${d}SKILL.md"
        if [ -f "$skill_md" ]; then
            fm_name=$(python3 -c "
import re, sys
with open(sys.argv[1]) as fh:
    content = fh.read()
m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
if m:
    fm = m.group(1)
    nm = re.search(r'^name:\s*[\"\\']?(.+?)[\"\\']?\s*$', fm, re.MULTILINE)
    if nm:
        print(nm.group(1))
    else:
        print('')
else:
    print('')
" "$skill_md" 2>/dev/null)
            if [ "$fm_name" = "$name" ]; then
                log_ok "Skill: ${name}"
            else
                log_warn "Skill: ${name} (frontmatter name mismatch: '${fm_name}')"
            fi
        else
            log_warn "Skill: ${name} (missing SKILL.md)"
        fi
        count=$((count + 1))
    done
    log_ok "Found ${count} skill(s)"
else
    log_warn "No skills directory"
fi

echo ""
echo "=== Command Discovery ==="
COMMANDS_DIR="${PROJECT_ROOT}/.opencode/commands"
if [ -d "$COMMANDS_DIR" ]; then
    count=0
    for f in "$COMMANDS_DIR"/*.md; do
        [ -f "$f" ] || continue
        name=$(basename "$f" .md)
        log_ok "Command: /${name}"
        count=$((count + 1))
    done
    log_ok "Found ${count} command(s)"

    echo ""
    echo "  Commands also defined in opencode.json:"
    python3 -c "
import json, sys
with open(sys.argv[1]) as fh:
    cfg = json.load(fh)
cmds = cfg.get('command', {})
for name in sorted(cmds.keys()):
    desc = cmds[name].get('description', '(no description)')
    print(f'    /{name}: {desc[:60]}')
" "$OPENCODE_JSON" 2>/dev/null
else
    log_warn "No commands directory"
fi

echo ""
echo "=== Serena ==="
SERENA_DIR="${PROJECT_ROOT}/.serena"
if [ -d "$SERENA_DIR" ]; then
    log_ok ".serena/ directory found"
    if [ -f "${SERENA_DIR}/project.yml" ]; then
        log_ok ".serena/project.yml found"
    else
        log_warn ".serena/project.yml not found"
    fi
    mem_count=$(find "${SERENA_DIR}/memories" -type f -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
    log_info "${mem_count} memory file(s)"
else
    log_warn ".serena/ directory not found"
fi

echo ""
echo "=== Git State ==="
if git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree &>/dev/null; then
    log_ok "Git repository detected"
    branch=$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo "detached")
    log_info "Current branch: ${branch}"
    dirty=$(git -C "$PROJECT_ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    if [ "$dirty" -gt 0 ]; then
        log_warn "${dirty} dirty file(s)"
    else
        log_ok "Working tree clean"
    fi
    if [ -f "${PROJECT_ROOT}/.git/info/exclude" ]; then
        # scripts/fullrepo_sync.py installs the canonical block marked by
        # `>>> rldyour fullrepo agent-only files >>>` / matching `<<<` close
        # marker. The legacy bootstrap_opencode.sh marker text
        # (`rldyour-opencode agent-only files`) is accepted as a fallback so
        # an older bootstrap still passes the doctor check.
        exclude_file="${PROJECT_ROOT}/.git/info/exclude"
        if grep -q ">>> rldyour fullrepo agent-only files >>>" "$exclude_file" 2>/dev/null; then
            log_ok "Agent-only exclude patterns installed (fullrepo block)"
        elif grep -q "rldyour-opencode agent-only files" "$exclude_file" 2>/dev/null; then
            log_ok "Agent-only exclude patterns installed (legacy bootstrap block)"
        else
            log_warn "Agent-only exclude patterns not installed (run scripts/fullrepo_sync.sh bootstrap-init)"
        fi
    fi
else
    log_warn "Not a git repository"
fi

echo ""
echo "========================================"
if [ "$ISSUES" -gt 0 ]; then
    echo -e " ${RED}${ISSUES} issue(s) found${NC}"
else
    echo -e " ${GREEN}No issues found${NC}"
fi
echo "========================================"
