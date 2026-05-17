#!/usr/bin/env bash
# rldyour-opencode dependency freshness check.
#
# Parses opencode.json and reports pinned npm / Python / Dart versions.
# Optionally compares each pin against the upstream registry (npm view +
# PyPI JSON API) and reports drift. Read-only; never edits opencode.json.
#
# Usage:
#   bash scripts/check_deps_freshness.sh                       # text pin report
#   bash scripts/check_deps_freshness.sh --json                # JSON pin report
#   bash scripts/check_deps_freshness.sh --check-freshness     # text + network freshness
#   bash scripts/check_deps_freshness.sh --check-freshness --json
#                                                              # JSON freshness envelope (CI)
#
# Exit codes:
#   0  all pinned versions current (or freshness check not requested)
#   1  drift detected: at least one pin lags behind upstream stable
#   2  setup error: opencode.json missing, helper missing, python missing,
#      or --strict + network errors prevented a comparison

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPENCODE_JSON="${PROJECT_ROOT}/opencode.json"
PYTHON="${PYTHON:-python3}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

OUTPUT_JSON=false
CHECK_FRESHNESS=false
STRICT=false
for arg in "$@"; do
    case "$arg" in
        --json) OUTPUT_JSON=true ;;
        --check-freshness) CHECK_FRESHNESS=true ;;
        --strict) STRICT=true ;;
        -h|--help)
            sed -n '1,30p' "$0"
            exit 0
            ;;
        *) echo "unknown flag: $arg" >&2; exit 2 ;;
    esac
done

log_err()  { $OUTPUT_JSON || echo -e "${RED}[ERR]${NC} $1" >&2; }
log_info() { $OUTPUT_JSON || echo -e "$1"; }
log_ok()   { $OUTPUT_JSON || echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { $OUTPUT_JSON || echo -e "${YELLOW}[WARN]${NC} $1"; }

if [ ! -f "$OPENCODE_JSON" ]; then
    log_err "opencode.json not found at ${OPENCODE_JSON}"
    exit 2
fi

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    log_err "$PYTHON not available on PATH"
    exit 2
fi

EXTRACT_SCRIPT="${PROJECT_ROOT}/scripts/_extract_pins.py"
if [ ! -f "$EXTRACT_SCRIPT" ]; then
    log_err "Missing helper: ${EXTRACT_SCRIPT}"
    exit 2
fi

PINS_JSON=$("$PYTHON" "$EXTRACT_SCRIPT" "$OPENCODE_JSON")

if ! $CHECK_FRESHNESS; then
    if $OUTPUT_JSON; then
        echo "$PINS_JSON"
        exit 0
    fi
    log_info "=== Pinned dependencies in opencode.json ==="
    echo "$PINS_JSON" | "$PYTHON" -c "
import json, sys
data = json.load(sys.stdin)
for entry in data['pins']:
    print(f\"  {entry['kind']:<6} {entry['name']:<60} {entry['version']}\")
print()
print(f\"Total pins: {data['count']}\")
"
    log_info ""
    log_info "Pass --check-freshness to query npm / PyPI for the latest stable version of each pin."
    exit 0
fi

# --- Freshness probe path -----------------------------------------------

FRESHNESS_SCRIPT="${PROJECT_ROOT}/scripts/_check_freshness.py"
if [ ! -f "$FRESHNESS_SCRIPT" ]; then
    log_err "Missing helper: ${FRESHNESS_SCRIPT}"
    exit 2
fi

FRESHNESS_ARGS=()
if $STRICT; then FRESHNESS_ARGS+=("--strict"); fi

set +e
FRESHNESS_JSON=$(echo "$PINS_JSON" | "$PYTHON" "$FRESHNESS_SCRIPT" "${FRESHNESS_ARGS[@]}")
FRESHNESS_EXIT=$?
set -e

if $OUTPUT_JSON; then
    echo "$FRESHNESS_JSON"
    exit "$FRESHNESS_EXIT"
fi

log_info "=== Dependency freshness report ==="
echo "$FRESHNESS_JSON" | "$PYTHON" -c "
import json, sys
data = json.load(sys.stdin)
for entry in data['pins']:
    status = entry.get('status', 'unknown')
    current = entry.get('version', '?')
    latest = entry.get('latest', '?') or '?'
    suffix = ''
    if 'error' in entry:
        suffix = f\"  ERROR={entry['error']}\"
    name = entry.get('name', '')
    kind = entry.get('kind', '?')
    print(f\"  [{status:<8}] {kind:<6} {name:<60} {current} -> {latest}{suffix}\")
print()
print(f\"Total pins: {data['count']}  Stale: {data['stale']}  Errors: {data['errors']}\")
"

if [ "$FRESHNESS_EXIT" -eq 0 ]; then
    log_ok "All pins are current."
elif [ "$FRESHNESS_EXIT" -eq 1 ]; then
    log_warn "At least one pin is stale. Review the report above."
else
    log_warn "Freshness probe encountered network errors. Re-run when registries are reachable."
fi

exit "$FRESHNESS_EXIT"
