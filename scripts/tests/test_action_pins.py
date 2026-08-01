"""Tests for scripts/check_action_pins.py."""
from __future__ import annotations

import subprocess
from pathlib import Path

import check_action_pins as cap


def _write_workflow(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "workflow.yml"
    path.write_text(body, encoding="utf-8")
    return path


def test_collect_action_pins_accepts_sha_and_semver_comment(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        """
jobs:
  test:
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0  # v7.0.0
      - uses: github/codeql-action/init@8533807ff379ac610d2b2c389c47e7c629d31d13  # v4.36.3
      - uses: ./local-action
      - uses: docker://alpine:3.20
""",
    )

    pins, errors = cap.collect_action_pins([path])

    assert errors == 0
    assert [(pin.action, pin.repo, pin.tag) for pin in pins] == [
        ("actions/checkout", "actions/checkout", "v7.0.0"),
        ("github/codeql-action/init", "github/codeql-action", "v4.36.3"),
    ]


def test_collect_action_pins_accepts_numeric_semver_comment(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        """
jobs:
  test:
    steps:
      - uses: NDDev-it-com/ci-workflows/.github/workflows/actionlint.yml@21bd3f7c3bbcbd7a9ecd3475b293d9e65aa8563a # 0.2.2
""",
    )

    pins, errors = cap.collect_action_pins([path])

    assert errors == 0
    assert [(pin.action, pin.repo, pin.tag) for pin in pins] == [
        (
            "NDDev-it-com/ci-workflows/.github/workflows/actionlint.yml",
            "NDDev-it-com/ci-workflows",
            "0.2.2",
        ),
    ]


def test_collect_action_pins_rejects_tag_only_uses(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        """
jobs:
  test:
    steps:
      - uses: actions/checkout@v7.0.0
""",
    )

    pins, errors = cap.collect_action_pins([path])

    assert pins == []
    assert errors == 1


def test_collect_action_pins_rejects_missing_inline_tag_comment(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        """
jobs:
  test:
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0
""",
    )

    pins, errors = cap.collect_action_pins([path])

    assert pins == []
    assert errors == 1


def test_remote_validation_accepts_dereferenced_annotated_tag(
    tmp_path: Path, monkeypatch
) -> None:
    path = _write_workflow(
        tmp_path,
        """
jobs:
  test:
    steps:
      - uses: github/codeql-action/init@8533807ff379ac610d2b2c389c47e7c629d31d13  # v4.36.3
""",
    )
    pins, errors = cap.collect_action_pins([path])
    assert errors == 0

    def _fake_run(*args, **kwargs):  # noqa: ANN001 - subprocess mock
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout=(
                "f52b05f4acaaa234e44466e66d29050e135ea9ef\trefs/tags/v4.36.3\n"
                "8533807ff379ac610d2b2c389c47e7c629d31d13\trefs/tags/v4.36.3^{}\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(cap.subprocess, "run", _fake_run)

    assert cap.validate_remote(pins, timeout=1.0) == 0


def test_remote_validation_rejects_comment_sha_drift(tmp_path: Path, monkeypatch) -> None:
    path = _write_workflow(
        tmp_path,
        """
jobs:
  test:
    steps:
      - uses: oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6  # v2.0.2
""",
    )
    pins, errors = cap.collect_action_pins([path])
    assert errors == 0

    def _fake_run(*args, **kwargs):  # noqa: ANN001 - subprocess mock
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout="4bc047ad259df6fc24a6c9b0f9a0cb08cf17fbe5\trefs/tags/v2.0.2\n",
            stderr="",
        )

    monkeypatch.setattr(cap.subprocess, "run", _fake_run)

    assert cap.validate_remote(pins, timeout=1.0) == 1


def test_main_runs_static_validation(tmp_path: Path) -> None:
    path = _write_workflow(
        tmp_path,
        """
jobs:
  test:
    steps:
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a  # v7.0.1
""",
    )

    assert cap.main([str(path)]) == 0
