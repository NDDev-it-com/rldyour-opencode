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
# Consistency review: [FAIL] is the 5th canonical tag introduced by the
# 0.12.2 validators (check_baseline_consistency.py, validate_mcp_profiles.py).
# Wrapping it here so shell-rendered lines pick up the same red color the
# validators emit on stderr, keeping the operator visual contract symmetric.
# shellcheck disable=SC2329  # helper reserved for future bash-level fail
#                            # tagging; today's [FAIL] lines come straight
#                            # from Python validator stderr.
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; }

MODE="${RY_OPENCODE_VALIDATE_MODE:-auto}"

usage() {
    cat <<'EOF'
Usage: bash scripts/validate_config.sh [--mode auto|static|installed|live]

Modes:
  auto       Static validation plus best-effort runtime probes when opencode is on PATH (default).
  static     No opencode binary and no network; validate repository files only.
  installed  Require a local opencode binary and run debug config/skill/agent probes.
  live       Installed mode plus network-backed dependency freshness check.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --mode)
            shift
            MODE="${1:?--mode requires auto, static, installed, or live}"
            case "$MODE" in
                auto|static|installed|live) ;;
                *)
                    log_err "Invalid --mode: ${MODE}"
                    usage >&2
                    exit 2
                    ;;
            esac
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_err "Unknown argument: $1"
            usage >&2
            exit 2
            ;;
    esac
    shift
done

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

log_step "GitHub Actions pins"
if python3 "${PROJECT_ROOT}/scripts/check_action_pins.py" "${PROJECT_ROOT}/.github/workflows"; then
    log_ok "GitHub Actions pins passed"
else
    ERRORS=$((ERRORS + 1))
fi

log_step "Baseline consistency (opencode-baseline.json)"
# Audit P0-1: docs / package.json / bun.lock / workflows must agree on the
# single OpenCode baseline. Hard-fail when they drift; soft warnings (e.g.
# CHANGELOG not yet mentioning the bumped plugin pin) print to stderr but
# do not flunk the gate.
if python3 "${PROJECT_ROOT}/scripts/check_baseline_consistency.py"; then
    log_ok "Baseline consistency passed"
else
    ERRORS=$((ERRORS + 1))
fi

log_step "MCP profile graph (mcp-profiles.json)"
# Audit P1-3: every server in opencode.json.mcp must belong to exactly one
# profile in references/mcp-profiles.json; every skill.requires_mcp must
# resolve to a declared MCP server; high-context dependencies emit a soft
# warning.
if python3 "${PROJECT_ROOT}/scripts/validate_mcp_profiles.py"; then
    log_ok "MCP profile graph passed"
else
    ERRORS=$((ERRORS + 1))
fi

log_step "Generated indexes"
if python3 "${PROJECT_ROOT}/scripts/generate_skills_index.py" --check --strict \
    && python3 "${PROJECT_ROOT}/scripts/generate_commands_index.py" --check --strict \
    && python3 "${PROJECT_ROOT}/scripts/generate_plugins_index.py" --check --strict; then
    log_ok "Generated indexes passed"
else
    ERRORS=$((ERRORS + 1))
fi

log_step "GitHub Actions script injection scan"
# Reviewer wave 2026-05-18 security F-3: `${{ inputs.* }}` and
# `${{ github.event.* }}` in `run:` blocks must be mapped through `env:`
# before reaching the shell; otherwise an attacker-controlled token can
# inject shell commands into the runner.
if python3 "${PROJECT_ROOT}/scripts/check_workflow_injection.py"; then
    log_ok "Workflow injection scan passed"
else
    ERRORS=$((ERRORS + 1))
fi

log_step "OpenCode plugin hook contract"
# Permission enforcement must not rely on typed-but-untriggered hooks such
# as `permission.ask`. This validator keeps security-critical plugins on
# documented/runtime-proven surfaces (`tool.execute.before`, `shell.env`)
# and catches accidental event.type values used as top-level hook keys.
if python3 "${PROJECT_ROOT}/scripts/check_plugin_hooks.py"; then
    log_ok "Plugin hook contract passed"
else
    ERRORS=$((ERRORS + 1))
fi

log_step "rldyour adapter contract"
# Canonical cross-tool IDs (domains, skills, commands, agents, lifecycle
# hooks) live in references/rldyour-contract.json. Validate the OpenCode
# adapter mapping against real local files and plugin hook subscriptions.
if python3 "${PROJECT_ROOT}/scripts/validate_contract.py"; then
    log_ok "Adapter contract passed"
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

log_step "Runtime resolution (opencode CLI)"
# `auto` keeps the historical local behavior: run runtime probes when the
# CLI is available and skip otherwise. `static`, `installed`, and `live`
# make CI/release lane intent explicit.
if [ "$MODE" = "static" ]; then
    log_info "static mode — skipping opencode CLI runtime probes"
elif command -v opencode >/dev/null 2>&1; then
    if opencode debug config >/dev/null 2>&1; then
        log_ok "opencode debug config resolved"
    else
        log_warn "opencode debug config FAILED (run opencode debug config for details)"
        ERRORS=$((ERRORS + 1))
    fi
    if opencode debug skill >/dev/null 2>&1; then
        log_ok "opencode debug skill resolved"
    else
        log_warn "opencode debug skill FAILED"
        ERRORS=$((ERRORS + 1))
    fi
    # `opencode debug agent build` is a cheap sanity probe against the
    # default primary agent. If the project's `agent.build` permission
    # block has a stale or PascalCase key, the resolver complains here.
    if opencode debug agent build >/dev/null 2>&1; then
        log_ok "opencode debug agent build resolved"
    else
        log_warn "opencode debug agent build FAILED"
        ERRORS=$((ERRORS + 1))
    fi
    if [ "$MODE" = "live" ]; then
        if bash "${PROJECT_ROOT}/scripts/check_deps_freshness.sh" --check-freshness --json >/dev/null; then
            log_ok "dependency freshness check passed"
        else
            log_err "dependency freshness check failed"
            ERRORS=$((ERRORS + 1))
        fi
    fi
else
    if [ "${RY_REQUIRE_OPENCODE_CLI:-0}" = "1" ] || [ "$MODE" = "installed" ] || [ "$MODE" = "live" ]; then
        log_err "opencode CLI not on PATH and installed runtime validation is required"
        ERRORS=$((ERRORS + 1))
    else
        log_info "opencode CLI not on PATH — skipping runtime resolution smoke"
    fi
fi

log_step "Summary"
if [ "$ERRORS" -eq 0 ]; then
    log_ok "All validation checks passed"
    exit 0
else
    log_err "${ERRORS} validation step(s) failed"
    exit 1
fi
