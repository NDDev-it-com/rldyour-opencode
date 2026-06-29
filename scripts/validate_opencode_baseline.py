#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    command = [sys.executable, "scripts/check_baseline_consistency.py"]
    proc = subprocess.run(command, cwd=ROOT, check=False)
    if proc.returncode == 0:
        print("ok: OpenCode baseline validation wrapper passed")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
