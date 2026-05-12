#!/usr/bin/env bash
# rldyour-opencode configuration validator.
#
# Delegates Python validation to scripts/_validate_helpers.py to avoid
# zsh-heredoc escape issues that broke earlier `python3 -c` blocks under
# `set -euo pipefail`. The helper module returns non-zero on any failure
# and prints structured [OK]/[ERR] lines.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HELPER="${PROJECT_ROOT}/scripts/_validate_helpers.py"
OPENCODE_JSON="${PROJECT_ROOT}/opencode.json"
VERSION_FILE="${PROJECT_ROOT}/VERSION"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_step() { echo -e "\n${YELLOW}=== $1 ===${NC}"; }
log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_err()  { echo -e "${RED}[ERR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

if [ ! -f "$HELPER" ]; then
    log_err "Missing Python helper: ${HELPER}"
    exit 1
fi

ERRORS=0

log_step "opencode.json"
if python3 "$HELPER" opencode_json "$OPENCODE_JSON"; then
    log_ok "opencode.json passed"
else
    ERRORS=$((ERRORS + 1))
fi

log_step "VERSION"
if python3 "$HELPER" version "$VERSION_FILE"; then
    log_ok "VERSION passed"
else
    ERRORS=$((ERRORS + 1))
fi

log_step "Skills"
SKILLS_DIR="${PROJECT_ROOT}/.opencode/skills"
if [ -d "$SKILLS_DIR" ]; then
    SKILL_PATHS=("$SKILLS_DIR"/*/)
    if [ ${#SKILL_PATHS[@]} -gt 0 ] && [ -d "${SKILL_PATHS[0]}" ]; then
        if python3 "$HELPER" skill "${SKILL_PATHS[@]}"; then
            log_ok "All skills passed"
        else
            ERRORS=$((ERRORS + 1))
        fi
    else
        log_info "No skill directories found"
    fi
else
    log_warn "No .opencode/skills directory"
fi

log_step "Agents"
AGENTS_DIR="${PROJECT_ROOT}/.opencode/agents"
if [ -d "$AGENTS_DIR" ]; then
    AGENT_PATHS=("$AGENTS_DIR"/*.md)
    if [ ${#AGENT_PATHS[@]} -gt 0 ] && [ -f "${AGENT_PATHS[0]}" ]; then
        if python3 "$HELPER" agent "${AGENT_PATHS[@]}"; then
            log_ok "All agents passed"
        else
            ERRORS=$((ERRORS + 1))
        fi
    else
        log_info "No agent files found"
    fi
else
    log_warn "No .opencode/agents directory"
fi

log_step "Commands"
COMMANDS_DIR="${PROJECT_ROOT}/.opencode/commands"
if [ -d "$COMMANDS_DIR" ]; then
    CMD_PATHS=("$COMMANDS_DIR"/*.md)
    if [ ${#CMD_PATHS[@]} -gt 0 ] && [ -f "${CMD_PATHS[0]}" ]; then
        if python3 "$HELPER" command "${CMD_PATHS[@]}"; then
            log_ok "All commands passed"
        else
            ERRORS=$((ERRORS + 1))
        fi
    else
        log_info "No command files found"
    fi
else
    log_warn "No .opencode/commands directory"
fi

log_step "Summary"
if [ "$ERRORS" -eq 0 ]; then
    log_ok "All validation checks passed"
    exit 0
else
    log_err "${ERRORS} validation step(s) failed"
    exit 1
fi
