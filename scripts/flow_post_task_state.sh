#!/usr/bin/env bash
# Compatibility wrapper for the policy-aware Python Flow state implementation.
set -euo pipefail

SCRIPT_DIR=$(CDPATH="" cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$SCRIPT_DIR/flow_post_task_state.py" "$@"
