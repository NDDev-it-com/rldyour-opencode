#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPENCODE_JSON="${PROJECT_ROOT}/opencode.json"
ERRORS=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_err()  { echo -e "${RED}[ERR]${NC} $1"; ERRORS=$((ERRORS + 1)); }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo "=== Validating rldyour-opencode configuration ==="
echo ""

if [ ! -f "$OPENCODE_JSON" ]; then
    log_err "opencode.json not found at ${OPENCODE_JSON}"
    exit 1
fi

echo "--- opencode.json JSON validity ---"
if python3 -c "import json, sys; json.load(open(sys.argv[1]))" "$OPENCODE_JSON" 2>/dev/null; then
    log_ok "opencode.json is valid JSON"
else
    log_err "opencode.json is not valid JSON"
fi

echo ""
echo "--- opencode.json required fields ---"
python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    cfg = json.load(f)

errors = 0

required_top = ['model']
for key in required_top:
    if key not in cfg:
        print(f'[ERR] Missing required top-level key: {key}')
        errors += 1
    else:
        print(f'[OK] Top-level key present: {key}')

if 'agent' in cfg:
    for name, agent in cfg['agent'].items():
        if 'description' not in agent and name != 'build' and name != 'plan':
            print(f'[WARN] Agent \"{name}\" missing description')
        if 'mode' in agent and agent['mode'] not in ('primary', 'subagent'):
            print(f'[ERR] Agent \"{name}\" has invalid mode: {agent[\"mode\"]}')
            errors += 1
        if 'permission' in agent and 'edit' in agent['permission']:
            val = agent['permission']['edit']
            if val not in ('allow', 'ask', 'deny'):
                print(f'[ERR] Agent \"{name}\" has invalid edit permission: {val}')
                errors += 1

if 'command' in cfg:
    for name, cmd in cfg['command'].items():
        if 'description' not in cmd:
            print(f'[ERR] Command \"{name}\" missing description')
            errors += 1
        else:
            print(f'[OK] Command \"{name}\" has description')

sys.exit(errors)
" "$OPENCODE_JSON" || ERRORS=$((ERRORS + 1))

echo ""
echo "--- Agent frontmatter validation ---"
AGENTS_DIR="${PROJECT_ROOT}/.opencode/agents"
if [ -d "$AGENTS_DIR" ]; then
    for agent_file in "$AGENTS_DIR"/*.md; do
        [ -f "$agent_file" ] || continue
        name=$(basename "$agent_file" .md)
        echo "  Checking agent: ${name}"

        has_frontmatter=false
        if head -1 "$agent_file" | grep -q '^---'; then
            has_frontmatter=true
        fi

        if [ "$has_frontmatter" = true ]; then
            log_ok "  ${name}: has frontmatter"
        else
            log_warn "  ${name}: missing YAML frontmatter (--- delimiters)"
        fi

        desc=$(python3 -c "
import re, sys
with open(sys.argv[1]) as f:
    content = f.read()
m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
if m:
    fm = m.group(1)
    dm = re.search(r'^description:\s*[\"']?(.+?)[\"']?\s*$', fm, re.MULTILINE)
    if dm:
        print(dm.group(1))
    else:
        print('')
else:
    print('')
" "$agent_file" 2>/dev/null)

        if [ -n "$desc" ]; then
            log_ok "  ${name}: has description (${#desc} chars)"
        else
            log_warn "  ${name}: missing description in frontmatter"
        fi
    done
else
    log_warn "No agents directory found at ${AGENTS_DIR}"
fi

echo ""
echo "--- Skill frontmatter validation ---"
SKILLS_DIR="${PROJECT_ROOT}/.opencode/skills"
if [ -d "$SKILLS_DIR" ]; then
    for skill_dir in "$SKILLS_DIR"/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")
        skill_md="${skill_dir}SKILL.md"
        echo "  Checking skill: ${skill_name}"

        if [ ! -f "$skill_md" ]; then
            log_err "  ${skill_name}: missing SKILL.md"
            continue
        fi

        fm_name=$(python3 -c "
import re, sys
with open(sys.argv[1]) as f:
    content = f.read()
m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
if m:
    fm = m.group(1)
    nm = re.search(r'^name:\s*[\"']?(.+?)[\"']?\s*$', fm, re.MULTILINE)
    if nm:
        print(nm.group(1))
    else:
        print('')
else:
    print('')
" "$skill_md" 2>/dev/null)

        if [ -n "$fm_name" ]; then
            if [ "$fm_name" = "$skill_name" ]; then
                log_ok "  ${skill_name}: name matches directory"
            else
                log_err "  ${skill_name}: name '${fm_name}' does not match directory '${skill_name}'"
            fi
        else
            log_err "  ${skill_name}: missing name in frontmatter"
        fi

        fm_desc=$(python3 -c "
import re, sys
with open(sys.argv[1]) as f:
    content = f.read()
m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
if m:
    fm = m.group(1)
    dm = re.search(r'^description:\s*[\"']?(.+?)[\"']?\s*$', fm, re.MULTILINE)
    if dm:
        print(dm.group(1))
    else:
        print('')
else:
    print('')
" "$skill_md" 2>/dev/null)

        if [ -n "$fm_desc" ]; then
            log_ok "  ${skill_name}: has description"
        else
            log_err "  ${skill_name}: missing description in frontmatter"
        fi

        name_len=${#skill_name}
        if [ "$name_len" -gt 64 ]; then
            log_err "  ${skill_name}: name exceeds 64 chars (${name_len})"
        fi

        if echo "$skill_name" | grep -qE '[^a-z0-9-]'; then
            log_err "  ${skill_name}: name is not kebab-case"
        fi
    done
else
    log_warn "No skills directory found at ${SKILLS_DIR}"
fi

echo ""
echo "--- Command frontmatter validation ---"
COMMANDS_DIR="${PROJECT_ROOT}/.opencode/commands"
if [ -d "$COMMANDS_DIR" ]; then
    for cmd_file in "$COMMANDS_DIR"/*.md; do
        [ -f "$cmd_file" ] || continue
        name=$(basename "$cmd_file" .md)
        echo "  Checking command: ${name}"

        has_frontmatter=false
        if head -1 "$cmd_file" | grep -q '^---'; then
            has_frontmatter=true
        fi

        if [ "$has_frontmatter" = true ]; then
            log_ok "  ${name}: has frontmatter"
        else
            log_warn "  ${name}: missing YAML frontmatter"
        fi

        desc=$(python3 -c "
import re, sys
with open(sys.argv[1]) as f:
    content = f.read()
m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
if m:
    fm = m.group(1)
    dm = re.search(r'^description:\s*[\"']?(.+?)[\"']?\s*$', fm, re.MULTILINE)
    if dm:
        print(dm.group(1))
    else:
        print('')
else:
    print('')
" "$cmd_file" 2>/dev/null)

        if [ -n "$desc" ]; then
            log_ok "  ${name}: has description"
        else
            log_warn "  ${name}: missing description in frontmatter"
        fi
    done
else
    log_warn "No commands directory found at ${COMMANDS_DIR}"
fi

echo ""
echo "=== Validation complete ==="
if [ "$ERRORS" -gt 0 ]; then
    echo -e "${RED}${ERRORS} error(s) found${NC}"
    exit 1
else
    echo -e "${GREEN}All checks passed${NC}"
    exit 0
fi
