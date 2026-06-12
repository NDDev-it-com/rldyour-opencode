from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_install_system_opencode_tolerates_missing_agent_docs(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            "bash",
            "scripts/install_system_opencode.sh",
            "--dry-run",
            "--global-config",
            "--force-project-install",
            "--target",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "ok: OpenCode project config planned" in proc.stdout
    if not (ROOT / "AGENTS.md").exists():
        assert "skip optional missing AGENTS.md" in proc.stdout
