from __future__ import annotations

import json
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = REPO_ROOT / "scripts" / "project_flow_policy.py"
STATE = REPO_ROOT / "scripts" / "flow_post_task_state.py"


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def init_repo(path: Path) -> None:
    git(path, "init")
    git(path, "checkout", "-b", "main")
    git(path, "config", "user.email", "opencode-policy@example.invalid")
    git(path, "config", "user.name", "OpenCode Policy")
    (path / "README.md").write_text("repo\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "init")


def write_policy(root: Path, payload: dict) -> None:
    (root / ".rldyour").mkdir(exist_ok=True)
    (root / ".rldyour/project-policy.json").write_text(json.dumps(payload), encoding="utf-8")


def test_policy_defaults_are_advisory_and_protect_dev(tmp_path: Path) -> None:
    init_repo(tmp_path)
    proc = subprocess.run(["python3", str(POLICY), "--json"], cwd=tmp_path, text=True, capture_output=True)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["effective"]["normal_branch_policy"]["agent_files"] == "allowed"
    assert payload["effective"]["serena"]["memory_storage"] == "normal-branch"
    assert payload["effective"]["branch_cleanup"]["mode"] == "advisory"
    assert "dev" in payload["effective"]["branch_cleanup"]["protected_branches"]
    assert payload["effective"]["execution"]["mode"] == "standard"
    assert payload["effective"]["cmux"]["enabled"] is False


def test_execution_and_cmux_policy_are_loaded(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_policy(
        tmp_path,
        {
            "schema_version": 1,
            "execution": {
                "mode": "orchestrator",
                "agent_role": "auto",
                "worker_agents": ["codex", "claude", "opencode"],
                "worker_count_min": 1,
                "worker_count_max": 3,
                "task_delegation": "explicit-orchestrator-only",
            },
            "cmux": {"enabled": True, "install_method": "brew-cask"},
        },
    )
    proc = subprocess.run(["python3", str(POLICY), "--json"], cwd=tmp_path, text=True, capture_output=True)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["valid"] is True
    assert payload["effective"]["execution"]["mode"] == "orchestrator"
    assert payload["effective"]["execution"]["worker_count_max"] == 3
    assert payload["effective"]["cmux"]["enabled"] is True


def test_tracked_ai_docs_policy_does_not_require_sync(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_policy(
        tmp_path,
        {
            "schema_version": 1,
            "normal_branch_policy": {
                "agent_files": "allowed",
                "ai_marker_additions": "allowed",
                "instruction_docs": "tracked-normal-branch",
            },
            "instruction_docs": {"mode": "tracked-normal-branch"},
            "branch_cleanup": {"mode": "advisory", "protected_branches": ["main", "dev"]},
            "stop_hook": {"block_on_branch_cleanup": False},
        },
    )
    (tmp_path / "AGENTS.md").write_text("agent docs\n", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude/CLAUDE.md").write_text("claude docs\n", encoding="utf-8")
    (tmp_path / ".serena/memories").mkdir(parents=True)
    (tmp_path / ".serena/memories/CORE-01-INDEX.md").write_text("memory\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "track ai docs")

    proc = subprocess.run(["python3", str(STATE)], cwd=tmp_path, text=True, capture_output=True)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["project_policy"]["source"] == ".rldyour/project-policy.json"
    assert payload["blocking_reasons"] == []
    assert payload["needs_flow_sync"] is False


def test_orchestrator_worker_reports_without_global_sync(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "README.md").write_text("repo\nworker change\n", encoding="utf-8")
    env = {
        **os_environ(),
        "RLDYOUR_EXECUTION_MODE": "orchestrator",
        "RLDYOUR_AGENT_ROLE": "worker",
        "RLDYOUR_WORKER_ID": "worker-opencode-test",
    }

    proc = subprocess.run(["python3", str(STATE)], cwd=tmp_path, env=env, text=True, capture_output=True)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["execution"]["agent_role"] == "worker"
    assert payload["execution"]["worker_id"] == "worker-opencode-test"
    assert "worker-report-required" in payload["blocking_reasons"]
    assert "branch-cleanup-required" not in payload["blocking_reasons"]


def test_dev_is_not_branch_cleanup_candidate(tmp_path: Path) -> None:
    init_repo(tmp_path)
    git(tmp_path, "checkout", "-b", "dev")
    git(tmp_path, "checkout", "main")

    proc = subprocess.run(["python3", str(STATE)], cwd=tmp_path, text=True, capture_output=True)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert "dev" not in payload["branch_cleanup_state"]["local_merged_branches"]
    assert payload["branch_cleanup_state"]["needs_cleanup"] is False


def os_environ() -> dict[str, str]:
    import os

    return os.environ.copy()
