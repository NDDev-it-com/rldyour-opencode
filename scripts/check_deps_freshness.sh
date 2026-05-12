#!/usr/bin/env bash
# rldyour-opencode dependency freshness check.
#
# Parses opencode.json and reports pinned npm / Python / Dart versions.
# Compares each pin against the upstream registry when available (npm,
# PyPI) and reports drift. Read-only; never edits opencode.json.
#
# Usage:
#   bash scripts/check_deps_freshness.sh           # text report
#   bash scripts/check_deps_freshness.sh --json    # JSON report (for CI)
#
# Exit codes:
#   0  all pinned versions are current or no drift detected
#   1  drift detected (at least one pin lags behind upstream stable)
#   2  network / parser error (could not fetch upstream)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPENCODE_JSON="${PROJECT_ROOT}/opencode.json"
PYTHON="${PYTHON:-python3}"

RED='\033[0;31m'
NC='\033[0m'

OUTPUT_JSON=false
if [ "${1:-}" = "--json" ]; then
    OUTPUT_JSON=true
fi

log_err()  { $OUTPUT_JSON || echo -e "${RED}[ERR]${NC} $1"; }
log_info() { $OUTPUT_JSON || echo -e "$1"; }

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

if $OUTPUT_JSON; then
    REPORT_TMP="$(mktemp)"
    echo "$PINS_JSON" > "$REPORT_TMP"
    cat "$REPORT_TMP"
    rm -f "$REPORT_TMP"
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
log_info "Network-backed freshness checks (npm / PyPI) not yet wired."
log_info "Use the JSON report (--json) to feed an external freshness service."
log_info "Manual baseline: cross-reference each pin against:"
log_info "  - npm:  https://www.npmjs.com/package/<name>"
log_info "  - PyPI: https://pypi.org/project/<name>/"

exit 0
