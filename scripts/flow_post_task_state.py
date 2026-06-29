#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from project_flow_policy import load_policy  # noqa: E402

RUNTIME_IGNORED = {
    ".serena/.sync_marker",
    ".serena/.serena_sync_state.json",
    ".serena/.auto_sync_head",
    ".serena/.active_workflow_intent.json",
    ".serena/.dirty_stop_ack",
    ".serena/.flow_sync_marker",
    ".serena/.flow_post_task_state.json",
    ".serena/.flow_blocker_ack.json",
    ".serena/.stop_lifecycle_timeout_marker",
    ".serena/.gitignore",
    ".serena/project.local.yml",
}
DOC_FILES = ("AGENTS.md", ".claude/CLAUDE.md", "CLAUDE.md")
PROTECTED_BRANCHES = {"main", "master", "dev", "develop", "development", "staging", "production", "prod"}
WORKFLOW_BRANCH_PREFIXES = ("ai/", "opencode/", "ry-", "rldyour/")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], check=False, capture_output=True, text=True)


def _stdout(*args: str) -> str:
    return _git(*args).stdout.strip()


def _subprocess_timeout() -> float:
    raw = os.environ.get("RLDYOUR_FLOW_SUBPROCESS_TIMEOUT_SECONDS", "10")
    try:
        return max(0.1, float(raw))
    except ValueError:
        return 10.0


def _runtime_path(path: str) -> bool:
    normalized = path.strip("/")
    return any(normalized == item or normalized.startswith(item.rstrip("/") + "/") for item in RUNTIME_IGNORED)


def _porcelain_paths() -> list[str]:
    raw = _git("status", "--porcelain", "--untracked-files=all").stdout.rstrip("\n")
    paths: list[str] = []
    for line in raw.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path and not _runtime_path(path):
            paths.append(path)
    return sorted(set(paths))


def _ahead_behind() -> tuple[int, int, str]:
    upstream = _stdout("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if not upstream:
        return 0, 0, ""
    counts = _stdout("rev-list", "--left-right", "--count", f"{upstream}...HEAD")
    try:
        behind_s, ahead_s = counts.split()
        return int(ahead_s), int(behind_s), upstream
    except ValueError:
        return 0, 0, upstream


def _worktree_count() -> int:
    raw = _stdout("worktree", "list", "--porcelain")
    return max(1, sum(1 for line in raw.splitlines() if line.startswith("worktree ")))


def _ref_exists(ref: str) -> bool:
    return _git("rev-parse", "--verify", "--quiet", ref).returncode == 0


def _default_cleanup_base() -> str:
    for candidate in ("origin/main", "main", "origin/master", "master"):
        if _ref_exists(candidate):
            return candidate
    return "HEAD"


def _effective_policy(policy: dict[str, Any]) -> dict[str, Any]:
    effective = policy.get("effective")
    return effective if isinstance(effective, dict) else {}


def _runtime_execution(effective_policy: dict[str, Any]) -> dict[str, Any]:
    execution_policy = effective_policy.get("execution")
    if not isinstance(execution_policy, dict):
        execution_policy = {}
    mode = os.environ.get("RLDYOUR_EXECUTION_MODE") or str(execution_policy.get("mode", "standard"))
    if mode not in {"standard", "orchestrator"}:
        mode = "standard"

    role = os.environ.get("RLDYOUR_AGENT_ROLE") or str(execution_policy.get("agent_role", "auto"))
    if role not in {"auto", "standalone", "orchestrator", "worker"}:
        role = "auto"
    if role == "auto":
        # Orchestrator activation is declarative (the user states the role in
        # /ry-init); only workers stay machine-identified through env.
        if mode == "orchestrator" and (
            os.environ.get("RLDYOUR_WORKER") == "1" or os.environ.get("RLDYOUR_WORKER_ID")
        ):
            role = "worker"
        else:
            role = "standalone"

    return {
        "execution_mode": mode,
        "agent_role": role,
        "task_delegation": str(execution_policy.get("task_delegation", "direct")),
        "cmux_workspace_id": os.environ.get("CMUX_WORKSPACE_ID", ""),
        "cmux_surface_id": os.environ.get("CMUX_SURFACE_ID", ""),
        "worker_id": os.environ.get("RLDYOUR_WORKER_ID", ""),
        "worker_allowed_paths": _split_worker_paths(os.environ.get("RLDYOUR_WORKER_ALLOWED_PATHS", "")),
    }


def _split_worker_paths(raw: str) -> list[str]:
    if not raw:
        return []
    normalized = raw.replace("\n", ",").replace(os.pathsep, ",")
    return sorted({part.strip().strip("/") for part in normalized.split(",") if part.strip().strip("/")})


def _path_matches_scope(path: str, scopes: list[str]) -> bool:
    normalized = path.strip("/")
    for scope in scopes:
        if normalized == scope or normalized.startswith(scope.rstrip("/") + "/"):
            return True
    return False


def _policy_list(section: dict[str, Any] | None, key: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(section, dict):
        return fallback
    value = section.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return fallback
    return tuple(value)


def _dict_section(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _local_merged_branches(base: str, current_branch: str, protected_branches: set[str]) -> list[str]:
    raw = _stdout("branch", "--format=%(refname:short)", "--merged", base)
    branches: list[str] = []
    for branch in raw.splitlines():
        branch = branch.strip()
        if branch and branch != current_branch and branch not in protected_branches:
            branches.append(branch)
    return sorted(set(branches))


def _remote_merged_branches(base: str, protected_branches: set[str]) -> list[str]:
    raw = _stdout("branch", "-r", "--format=%(refname:short)", "--merged", base)
    branches: list[str] = []
    for ref in raw.splitlines():
        ref = ref.strip()
        if not ref or ref.endswith("/HEAD") or " -> " in ref or "/" not in ref:
            continue
        branch = ref.split("/", 1)[1]
        if branch not in protected_branches:
            branches.append(ref)
    return sorted(set(branches))


def _workflow_branch(branch: str, prefixes: tuple[str, ...]) -> bool:
    normalized = branch.split("/", 1)[1] if branch.startswith("origin/") else branch
    return normalized.startswith(prefixes)


def _branch_cleanup_state(current_branch: str, policy: dict[str, Any]) -> dict[str, Any]:
    effective = _effective_policy(policy)
    branches_policy = _dict_section(effective.get("branches"))
    cleanup_policy = _dict_section(effective.get("branch_cleanup"))
    protected_branches = set(PROTECTED_BRANCHES)
    protected_branches.update(branches_policy.get("protected_branches", []))
    protected_branches.update(cleanup_policy.get("protected_branches", []))
    workflow_prefixes = _policy_list(cleanup_policy, "workflow_branch_prefixes", WORKFLOW_BRANCH_PREFIXES)
    blocking_prefixes = _policy_list(cleanup_policy, "blocking_prefixes", workflow_prefixes)
    cleanup_mode = str(cleanup_policy.get("mode", "advisory"))
    block_stop = bool(cleanup_policy.get("block_stop")) or cleanup_mode == "strict"
    base = _default_cleanup_base()
    local_merged = _local_merged_branches(base, current_branch, protected_branches)
    remote_merged = _remote_merged_branches(base, protected_branches)
    workflow_local = [branch for branch in local_merged if _workflow_branch(branch, workflow_prefixes)]
    workflow_remote = [branch for branch in remote_merged if _workflow_branch(branch, workflow_prefixes)]
    blocking_local: list[str] = []
    blocking_remote: list[str] = []
    advisory_local: list[str] = []
    advisory_remote: list[str] = []
    if cleanup_mode == "strict" and block_stop:
        blocking_local = [branch for branch in local_merged if _workflow_branch(branch, blocking_prefixes)]
        blocking_remote = [branch for branch in remote_merged if _workflow_branch(branch, blocking_prefixes)]
        advisory_local = [branch for branch in local_merged if branch not in blocking_local]
        advisory_remote = [branch for branch in remote_merged if branch not in blocking_remote]
    elif cleanup_mode != "disabled":
        advisory_local = local_merged
        advisory_remote = remote_merged
    blocking_candidates: list[Any] = [*blocking_local, *blocking_remote]
    advisory_candidates: list[Any] = [*advisory_local, *advisory_remote]
    return {
        "base": base,
        "mode": cleanup_mode,
        "block_stop": block_stop,
        "protected_branches": sorted(protected_branches),
        "local_merged_branches": local_merged,
        "remote_merged_branches": remote_merged,
        "merged_workflow_branches": sorted(set(workflow_local + workflow_remote)),
        "worktree_cleanup_candidates": [],
        "blocking_local_branches": blocking_local,
        "blocking_remote_branches": blocking_remote,
        "blocking_worktree_candidates": [],
        "blocking_candidates": blocking_candidates,
        "advisory_local_branches": advisory_local,
        "advisory_remote_branches": advisory_remote,
        "advisory_worktree_candidates": [],
        "advisory_candidates": advisory_candidates,
        "needs_cleanup": bool(blocking_candidates),
    }


def _instruction_docs_state(root: Path, dirty_files: list[str], policy: dict[str, Any]) -> dict[str, Any]:
    effective = _effective_policy(policy)
    normal_policy = _dict_section(effective.get("normal_branch_policy"))
    instruction_policy = _dict_section(effective.get("instruction_docs"))
    instruction_docs_mode = str(instruction_policy.get("mode", "tracked-normal-branch"))
    normal_instruction_mode = str(normal_policy.get("instruction_docs", "tracked-normal-branch"))
    if instruction_docs_mode not in {"tracked-normal-branch", "disabled"}:
        instruction_docs_mode = normal_instruction_mode
    present_docs = [path for path in DOC_FILES[:2] if (root / path).is_file()]
    missing_docs = [path for path in DOC_FILES[:2] if not (root / path).is_file()]
    dirty_instruction_docs = [path for path in dirty_files if path in DOC_FILES]
    review_reasons: list[str] = []
    if dirty_instruction_docs:
        review_reasons.append("instruction docs have uncommitted changes")
    if instruction_docs_mode == "disabled":
        review_reasons = []
    return {
        "instruction_docs_mode": instruction_docs_mode,
        "policy_source": policy.get("source"),
        "policy_source_kind": policy.get("source_kind"),
        "required_docs": list(DOC_FILES[:2]),
        "present_docs": present_docs,
        "missing_docs": missing_docs,
        "dirty_instruction_docs": dirty_instruction_docs,
        "review_reasons": review_reasons,
        "needs_instruction_docs_review": bool(review_reasons),
    }


def _serena_state(root: Path) -> tuple[bool, dict[str, Any]]:
    memories = root / ".serena" / "memories"
    sync_marker = root / ".serena" / ".serena_sync_state.json"
    count = sum(1 for path in memories.rglob("*.md") if path.is_file()) if memories.is_dir() else 0
    current = not sync_marker.is_file()
    return current, {"memory_count": count, "memories_current": "fresh" if current else "stale"}


def state() -> dict[str, Any]:
    if _git("rev-parse", "--is-inside-work-tree").returncode != 0:
        return {"is_git_repo": False, "needs_flow_sync": False, "sync_needed": False, "serena_current": True}

    root = Path(_stdout("rev-parse", "--show-toplevel") or ".").resolve()
    project_policy = load_policy(root)
    effective = _effective_policy(project_policy)
    stop_policy = _dict_section(effective.get("stop_hook"))
    serena_policy = _dict_section(effective.get("serena"))
    runtime_execution = _runtime_execution(effective)
    execution_mode = str(runtime_execution["execution_mode"])
    agent_role = str(runtime_execution["agent_role"])
    is_worker = execution_mode == "orchestrator" and agent_role == "worker"
    branch = _stdout("branch", "--show-current") or "detached"
    head_full = _stdout("rev-parse", "HEAD")
    head_sha = head_full[:7] if head_full else "unknown"
    dirty_files = _porcelain_paths()
    ahead, behind, upstream = _ahead_behind()
    serena_current, serena_state = _serena_state(root)
    instruction_docs_state = _instruction_docs_state(root, dirty_files, project_policy)
    branch_cleanup_state = _branch_cleanup_state(branch, project_policy)

    blocking_reasons: list[str] = []
    advisory_reasons: list[str] = []
    if is_worker:
        worker_scopes = runtime_execution.get("worker_allowed_paths")
        worker_scopes = worker_scopes if isinstance(worker_scopes, list) else []
        dirty_out_of_scope = [path for path in dirty_files if worker_scopes and not _path_matches_scope(path, worker_scopes)]
        if dirty_out_of_scope:
            blocking_reasons.append("worker-dirty-out-of-scope")
        if dirty_files and bool(stop_policy.get("block_on_dirty_source", True)):
            blocking_reasons.append("worker-report-required")
        if not serena_current and str(serena_policy.get("mode", "enabled")) != "disabled":
            advisory_reasons.append("worker-serena-stale-report")
        if ahead or behind:
            advisory_reasons.append("worker-branch-drift-report")
        if bool(branch_cleanup_state.get("needs_cleanup")):
            advisory_reasons.append("worker-branch-cleanup-report")
        if bool(instruction_docs_state.get("needs_instruction_docs_review")):
            advisory_reasons.append("worker-instruction-docs-report")
    else:
        if not serena_current and str(serena_policy.get("mode", "enabled")) != "disabled":
            blocking_reasons.append("serena-memory-stale")
        if dirty_files and bool(stop_policy.get("block_on_dirty_source", True)):
            blocking_reasons.append("dirty-worktree")
        if (ahead or behind) and bool(stop_policy.get("block_on_ahead_behind", True)):
            blocking_reasons.append("branch-ahead-behind")
        branch_cleanup_blocks_stop = bool(stop_policy.get("block_on_branch_cleanup", False)) or bool(
            branch_cleanup_state.get("block_stop")
        )
        if branch_cleanup_state.get("needs_cleanup") and branch_cleanup_blocks_stop:
            blocking_reasons.append("branch-cleanup-required")
        elif branch_cleanup_state.get("advisory_candidates"):
            advisory_reasons.append("branch-cleanup-advisory")
        if instruction_docs_state.get("needs_instruction_docs_review"):
            blocking_reasons.append("instruction-docs-review")

    fingerprint_payload = {
        "head": head_full,
        "branch": branch,
        "dirty": dirty_files,
        "ahead": ahead,
        "behind": behind,
        "blocking_reasons": blocking_reasons,
        "advisory_reasons": advisory_reasons,
        "policy_source": project_policy.get("source"),
        "branch_cleanup": branch_cleanup_state,
        "execution": runtime_execution,
    }
    fingerprint = hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True).encode()).hexdigest()[:16]
    needs_flow_sync = bool(blocking_reasons)
    return {
        "is_git_repo": True,
        "head_sha": head_sha,
        "head_full": head_full,
        "branch": branch,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "dirty_files": dirty_files,
        "dirty_count": len(dirty_files),
        "doc_files_present": [path for path in DOC_FILES if (root / path).is_file()],
        "doc_files_changed": [path for path in dirty_files if path in DOC_FILES],
        "worktree_count": _worktree_count(),
        "serena_current": serena_current,
        "serena_state": serena_state,
        "execution": runtime_execution,
        "project_policy": {
            "source": project_policy.get("source"),
            "source_kind": project_policy.get("source_kind"),
            "profile": effective.get("profile"),
            "valid": project_policy.get("valid"),
            "errors": project_policy.get("errors", []),
            "warnings": project_policy.get("warnings", []),
            "effective": effective,
        },
        "instruction_docs_state": instruction_docs_state,
        "branch_cleanup_state": branch_cleanup_state,
        "blocking_reasons": blocking_reasons,
        "advisory_reasons": advisory_reasons,
        "needs_flow_sync": needs_flow_sync,
        "sync_needed": needs_flow_sync,
        "fingerprint": fingerprint,
        "git": {
            "branch": branch,
            "head_sha": head_sha,
            "dirty": bool(dirty_files),
            "dirty_files": len(dirty_files),
            "ahead": ahead,
            "behind": behind,
        },
        "serena": serena_state,
        "instruction_docs": {"agents_md": (root / "AGENTS.md").is_file()},
    }


def main() -> int:
    print(json.dumps(state(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
