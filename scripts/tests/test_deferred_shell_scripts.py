"""Tests for operational shell scripts listed in verification backlog (F-4).

The deferred items in the opencode summary are all currently executable
scripts without direct unit coverage.  These tests add focused, local
contracts for each script while avoiding dependency on global host tooling
by providing temporary PATH stubs when needed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

DEFAULT_TIMEOUT = 10
ALL_TIMEOUT = 30

SCRIPT_NAMES = (
    "bootstrap_opencode.sh",
    "check_lsps.sh",
    "collect_diagnostics.sh",
    "deploy_readiness.sh",
    "detect_project_checks.sh",
    "flow_post_task_state.sh",
    "git_sync_audit.sh",
    "install_lsps.sh",
)


def _copy_script(tmp_root: Path, name: str) -> Path:
    scripts_dir = tmp_root / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    src = SCRIPTS_DIR / name
    dst = scripts_dir / name
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    dst.chmod(0o755)
    if name == "flow_post_task_state.sh":
        for companion in ("flow_post_task_state.py", "project_flow_policy.py"):
            companion_src = SCRIPTS_DIR / companion
            companion_dst = scripts_dir / companion
            companion_dst.write_text(companion_src.read_text(encoding="utf-8"), encoding="utf-8")
            companion_dst.chmod(0o755)
    return dst


def _run_script(
    script: Path,
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(script), *args],
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _init_git_repo(tmp_root: Path) -> None:
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=tmp_root,
        check=True,
        capture_output=True,
        timeout=DEFAULT_TIMEOUT,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_root,
        check=True,
        capture_output=True,
        timeout=DEFAULT_TIMEOUT,
    )
    subprocess.run(
        ["git", "config", "user.name", "Shell Script Test"],
        cwd=tmp_root,
        check=True,
        capture_output=True,
        timeout=DEFAULT_TIMEOUT,
    )
    (tmp_root / "README.md").write_text("# fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_root, check=True, capture_output=True, timeout=DEFAULT_TIMEOUT)
    subprocess.run(
        ["git", "commit", "-m", "fixture commit"],
        cwd=tmp_root,
        check=True,
        capture_output=True,
        timeout=DEFAULT_TIMEOUT,
    )


def _make_stub(bin_dir: Path, name: str, code: int = 0) -> None:
    target = bin_dir / name
    target.write_text(f"#!/usr/bin/env bash\nexit {code}\n", encoding="utf-8")
    target.chmod(0o755)


def _commit_script_copy(tmp_root: Path, script_path: Path) -> None:
    subprocess.run(
        ["git", "add", str(script_path)],
        cwd=tmp_root,
        check=True,
        capture_output=True,
        timeout=DEFAULT_TIMEOUT,
    )
    subprocess.run(
        ["git", "commit", "-m", f"add {script_path.name}"],
        cwd=tmp_root,
        check=True,
        capture_output=True,
        timeout=DEFAULT_TIMEOUT,
    )


@pytest.mark.parametrize("script_name", SCRIPT_NAMES)
def test_shell_scripts_have_bash_and_strict_mode(script_name: str) -> None:
    text = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text


def test_bootstrap_opencode_adds_and_reuses_excludes(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "opencode.json").write_text('{"model":"test"}\n', encoding="utf-8")
    script = _copy_script(tmp_path, "bootstrap_opencode.sh")
    exclude = tmp_path / ".git" / "info" / "exclude"
    result1 = _run_script(script, [], cwd=tmp_path, timeout=ALL_TIMEOUT)
    assert result1.returncode == 0
    text1 = exclude.read_text(encoding="utf-8")
    assert "rldyour-opencode agent-only files" in text1

    result2 = _run_script(script, [], cwd=tmp_path, timeout=ALL_TIMEOUT)
    assert result2.returncode == 0
    text2 = exclude.read_text(encoding="utf-8")
    # Idempotent marker insertion.
    assert text2.count("rldyour-opencode agent-only files") == 2


def test_bootstrap_opencode_fails_without_opencode_json(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    script = _copy_script(tmp_path, "bootstrap_opencode.sh")
    result = _run_script(script, [], cwd=tmp_path, timeout=ALL_TIMEOUT)
    assert result.returncode == 1
    assert "opencode.json not found" in result.stdout + result.stderr


def test_check_lsps_passes_when_all_stubs_present(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    script = _copy_script(tmp_path, "check_lsps.sh")

    # Install fake command providers for every language-server check.
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    for cmd in (
        "pyright-langserver",
        "ruff",
        "typescript-language-server",
        "rust-analyzer",
        "dart",
        "gopls",
        "clangd",
        "yaml-language-server",
        "bash-language-server",
        "shellcheck",
        "vscode-html-language-server",
        "vscode-css-language-server",
        "vscode-json-language-server",
        "docker-language-server",
        "taplo",
        "marksman",
    ):
        _make_stub(stub_bin, cmd)

    # Satisfy all "project prereq" checks to keep output in green state.
    for marker in (
        "pyproject.toml",
        "tsconfig.json",
        "Cargo.toml",
        "pubspec.yaml",
        "go.mod",
        "compile_commands.json",
        "Dockerfile",
    ):
        (tmp_path / marker).write_text("# stub\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env.get('PATH', '')}"
    result = _run_script(script, [], cwd=tmp_path, env=env, timeout=ALL_TIMEOUT)
    assert result.returncode == 0
    assert "All checks passed." in result.stdout


def test_collect_diagnostics_creates_bundle(tmp_path: Path) -> None:
    bundle_root = tmp_path / "diagnostics"
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    opencode_stub = stub_bin / "opencode"
    opencode_stub.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"${1:-}\" = \"--version\" ]; then echo '1.17.7'; exit 0; fi\n"
        "echo '{\"stub\":\"opencode\"}'\n",
        encoding="utf-8",
    )
    opencode_stub.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env.get('PATH', '')}"
    result = _run_script(
        SCRIPTS_DIR / "collect_diagnostics.sh",
        ["--output", str(bundle_root)],
        cwd=PROJECT_ROOT,
        env=env,
        timeout=120,
    )
    assert result.returncode == 0
    bundle = Path(result.stdout.strip())
    assert bundle.exists()
    assert bundle.is_dir()
    assert (bundle / "git-status.txt").exists()
    assert (bundle / "flow-state.json").exists()
    assert (bundle / "git-audit.txt").exists()
    assert (bundle / "mcp-smoke.json").exists()
    assert (bundle / "env.txt").exists()
    assert "[collect] bundle ready" in result.stderr + result.stdout


def test_collect_diagnostics_prints_help_for_flag() -> None:
    result = _run_script(SCRIPTS_DIR / "collect_diagnostics.sh", ["--help"], cwd=PROJECT_ROOT, timeout=DEFAULT_TIMEOUT)
    assert result.returncode == 0
    assert "rldyour-opencode diagnostic bundle." in result.stdout


def test_collect_diagnostics_rejects_unknown_arg(tmp_path: Path) -> None:
    result = _run_script(SCRIPTS_DIR / "collect_diagnostics.sh", ["--does-not-exist"], cwd=PROJECT_ROOT, timeout=DEFAULT_TIMEOUT)
    assert result.returncode == 2
    assert "Unknown arg: --does-not-exist" in result.stderr


def test_deploy_readiness_passes_on_clean_main_repo(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    script = _copy_script(tmp_path, "deploy_readiness.sh")
    _commit_script_copy(tmp_path, script)
    result = _run_script(script, [], cwd=tmp_path, timeout=ALL_TIMEOUT)
    assert result.returncode == 0
    assert "Deploy readiness: PASS" in result.stdout


def test_deploy_readiness_fails_on_dirty_tree(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "dirty.txt").write_text("x", encoding="utf-8")
    script = _copy_script(tmp_path, "deploy_readiness.sh")
    result = _run_script(script, [], cwd=tmp_path, timeout=ALL_TIMEOUT)
    assert result.returncode == 1
    assert "Deploy readiness: FAIL" in result.stdout


def test_deploy_readiness_passes_when_clean(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    script = _copy_script(tmp_path, "deploy_readiness.sh")
    _commit_script_copy(tmp_path, script)
    result = _run_script(script, [], cwd=tmp_path, timeout=ALL_TIMEOUT)
    assert result.returncode == 0
    assert "Deploy readiness: PASS" in result.stdout


def test_detect_project_checks_detects_configured_runners(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    for name in (
        "pyproject.toml",
        "tsconfig.json",
        "Cargo.toml",
        "go.mod",
        "pubspec.yaml",
        "Dockerfile",
        "package.json",
    ):
        (tmp_path / name).write_text("{}", encoding="utf-8")

    # Stubs for command prefixes used by detect_project_checks.
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    for cmd in (
        "pytest",
        "ruff",
        "flake8",
        "pyright",
        "mypy",
        "npm",
        "pnpm",
        "yarn",
        "bunx",
        "cargo",
        "go",
        "flutter",
        "dart",
        "docker",
    ):
        _make_stub(stub_bin, cmd)

    script = _copy_script(tmp_path, "detect_project_checks.sh")
    _commit_script_copy(tmp_path, script)
    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env.get('PATH', '')}"
    result = _run_script(script, [], cwd=tmp_path, env=env, timeout=ALL_TIMEOUT)
    assert result.returncode == 0
    assert "  test: pytest (detected from pyproject.toml)" in result.stdout
    assert "  lint: pytest" not in result.stdout
    assert "  lint: ruff check . (detected from pyproject.toml)" in result.stdout
    assert "  typecheck: pyright (detected from pyproject.toml)" in result.stdout


def test_detect_project_checks_reports_none_when_no_manifests(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    script = _copy_script(tmp_path, "detect_project_checks.sh")
    result = _run_script(script, [], cwd=tmp_path, timeout=DEFAULT_TIMEOUT)
    assert result.returncode == 0
    assert "No language stack manifests found in this directory." in result.stdout


def test_flow_post_task_state_is_valid_json(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    memory_dir = tmp_path / ".serena" / "memories"
    (memory_dir / "one.md").parent.mkdir(parents=True)
    (memory_dir / "one.md").write_text("{}", encoding="utf-8")
    script = _copy_script(tmp_path, "flow_post_task_state.sh")
    result = _run_script(script, [], cwd=tmp_path, timeout=DEFAULT_TIMEOUT)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert set(payload.keys()) >= {"git", "serena", "instruction_docs", "sync_needed"}
    assert isinstance(payload["git"]["dirty"], bool)
    assert payload["serena"]["memory_count"] == 1


def test_flow_post_task_state_flags_dirty_sync_needed(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "dirty.txt").write_text("x", encoding="utf-8")
    script = _copy_script(tmp_path, "flow_post_task_state.sh")
    result = _run_script(script, [], cwd=tmp_path, timeout=ALL_TIMEOUT)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["git"]["dirty"] is True
    assert payload["git"]["dirty_files"] >= 1
    assert payload["sync_needed"] is True


def test_git_sync_audit_reports_branch_and_dirty(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    script = _copy_script(tmp_path, "git_sync_audit.sh")
    _commit_script_copy(tmp_path, script)
    result = _run_script(script, [], cwd=tmp_path, timeout=DEFAULT_TIMEOUT)
    assert result.returncode == 0
    assert "Branch: main" in result.stdout
    assert "Dirty files:" in result.stdout
    assert "Worktrees:" in result.stdout


def test_install_lsps_fails_when_brew_is_missing(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    script = _copy_script(tmp_path, "install_lsps.sh")
    # Execute in PATH that purposely lacks `brew`.
    env = os.environ.copy()
    env["PATH"] = str(tmp_path / "no-brew")
    (tmp_path / "no-brew").mkdir()
    result = _run_script(script, [], cwd=tmp_path, env=env, timeout=ALL_TIMEOUT)
    assert result.returncode == 1
    assert "Error: Homebrew is required." in result.stdout


def test_install_lsps_runs_health_check_with_all_stubs(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    script = _copy_script(tmp_path, "install_lsps.sh")
    # install_lsps invokes check_lsps using dirname("$0"), so we need the sibling copy.
    _copy_script(tmp_path, "check_lsps.sh")

    # Create temporary stubs for brew + required commands.
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _make_stub(stub_bin, "brew", code=0)
    for cmd in (
        "pyright-langserver",
        "ruff",
        "typescript-language-server",
        "rust-analyzer",
        "dart",
        "gopls",
        "clangd",
        "yaml-language-server",
        "bash-language-server",
        "shellcheck",
        "vscode-html-language-server",
        "vscode-css-language-server",
        "vscode-json-language-server",
        "docker-language-server",
        "taplo",
        "marksman",
        "qmlls",
        "rustup",
    ):
        _make_stub(stub_bin, cmd)

    # satisfy check_lsps project-prereq checks
    for marker in (
        "pyproject.toml",
        "tsconfig.json",
        "Cargo.toml",
        "pubspec.yaml",
        "go.mod",
        "compile_commands.json",
        "Dockerfile",
    ):
        (tmp_path / marker).write_text("# stub\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env.get('PATH', '')}"
    result = _run_script(script, [], cwd=tmp_path, env=env, timeout=ALL_TIMEOUT)
    assert result.returncode == 0
    assert "Running health check..." in result.stdout
    assert "All checks passed." in result.stdout
