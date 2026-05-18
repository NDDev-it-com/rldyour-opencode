#!/usr/bin/env bash
# Thin wrapper around scripts/doctor_opencode.py. The Python core owns
# every check, every subprocess timeout, and the JSON envelope. This
# script exists so the historical `bash scripts/doctor_opencode.sh`
# invocation keeps working — same exit codes, same text output.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "${SCRIPT_DIR}/doctor_opencode.py" "$@"
