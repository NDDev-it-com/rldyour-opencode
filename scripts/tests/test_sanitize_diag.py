"""Tests for scripts/_sanitize_diag.py credential-pattern stripper.

Each test feeds a synthetic credential-shaped fixture (NOT a real
credential) into sanitize() and asserts the redaction marker replaces
the substring. Closes audit finding 4MUSTHAVE PA-011 "Cover diagnostic
redaction patterns".

Fixture-secret-shape disclaimer: every literal token in this file is a
purpose-built test fixture matching only the regex pattern shape. None
of them grant access to any real system.
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest

# sys.path setup happens in conftest.py at session start.
import _sanitize_diag as sd  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SANITIZE_PY = PROJECT_ROOT / "scripts" / "_sanitize_diag.py"


# ---------- Per-pattern coverage ----------


@pytest.mark.parametrize(
    "raw,redacted",
    [
        # Context7 vendor prefix MUST match before generic sk-.
        ("ctx7sk-aaaaaaaa11111111", "<redacted-context7-key>"),
        ("ctx7sk-zzzz1234ABCD", "<redacted-context7-key>"),
        # Anthropic vendor prefix.
        ("sk-ant-fixtureSAMPLE12345", "<redacted-anthropic-key>"),
        # OpenAI project key prefix.
        ("sk-proj-FIXTURE0987654321", "<redacted-openai-project-key>"),
        # Generic OpenAI/Anthropic-shape sk- token.
        ("sk-FIXTURE12345abcd", "<redacted-api-key>"),
        # GitHub fine-grained PAT.
        ("github_pat_FIXTURE1234567890abcdefABCDEF", "<redacted-gh-fine-grained-pat>"),
        # GitHub classic PAT.
        ("ghp_AAAA1111BBBB2222", "<redacted-gh-pat>"),
        # GitHub server-to-server.
        ("ghs_CCCC3333DDDD4444", "<redacted-gh-server-token>"),
        # GitHub OAuth.
        ("gho_EEEE5555FFFF6666", "<redacted-gh-oauth>"),
        # GitLab PAT.
        ("glpat-FIXTURE99887766", "<redacted-gitlab-pat>"),
        # AWS access key id (exactly 20 chars).
        ("AKIAFIXTURE000000123", "<redacted-aws-access-key>"),
        # AWS session access key id.
        ("ASIAFIXTURE000000456", "<redacted-aws-session-key>"),
        # Slack token.
        ("xoxb-FIXTURE-12345-abcde", "<redacted-slack-token>"),
        # JWT (three dot-separated base64url segments, each >=20 chars).
        (
            "eyJabcdefghijklmnopqrstuv.payload12345abcdefghijklmn.signaturefixture12345678",
            "<redacted-jwt>",
        ),
    ],
)
def test_each_pattern_redacted(raw: str, redacted: str) -> None:
    output = sd.sanitize(f"prefix {raw} suffix")
    assert raw not in output, f"raw {raw!r} leaked through sanitizer"
    assert redacted in output, f"expected marker {redacted!r} missing in {output!r}"


# ---------- PEM block coverage ----------


def test_pem_block_redacted() -> None:
    raw = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "AAAAB3NzaC1yc2EAAAADAQABAAABAQDfixtureKey\n"
        "endbody\n"
        "-----END OPENSSH PRIVATE KEY-----"
    )
    output = sd.sanitize(f"header\n{raw}\nfooter")
    assert "AAAAB3" not in output
    assert "<redacted-pem>" in output


# ---------- Order sensitivity ----------


def test_more_specific_prefix_wins_over_generic_sk() -> None:
    """ctx7sk- MUST match before the generic sk- pattern. Lookbehind
    on the generic sk- also defends against an order regression that
    would otherwise let the generic pattern eat into a longer compound."""
    raw = "ctx7sk-FIXTURE_should_render_as_context7_marker"
    output = sd.sanitize(raw)
    assert "<redacted-context7-key>" in output
    assert "<redacted-api-key>" not in output


def test_sk_pattern_does_not_eat_inside_compound() -> None:
    """Even if pattern order regresses, the lookbehind on the generic
    sk- pattern means an `sk-` substring inside a longer dash-bounded
    token is not eaten. The vendor prefix wins, the inner sk-... stays
    intact."""
    raw = "ctx7sk-FIXTUREinnerpayload"
    output = sd.sanitize(raw)
    assert "<redacted-context7-key>" in output


# ---------- False-positive defenses ----------


def test_short_strings_not_matched() -> None:
    """The PATTERN tail `{8,}` should not match strings shorter than 8 chars."""
    raw = "sk-abc"  # only 3 chars after prefix
    output = sd.sanitize(raw)
    assert raw in output, "short non-credential string should not be redacted"


def test_commit_sha_is_safe() -> None:
    """40-hex commit SHAs would be caught by an opaque 32+ char fallback
    if it existed; since _sanitize_diag.py intentionally DOES NOT enable
    that fallback (per its module docstring), they pass through."""
    sha = "1e14c22f29c6abcdef0123456789abcdef012345"
    output = sd.sanitize(f"HEAD: {sha}")
    assert sha in output


def test_dependency_pin_is_safe() -> None:
    pin = "serena-agent==1.3.0"
    output = sd.sanitize(pin)
    assert pin in output


# ---------- CLI dispatch ----------


def test_cli_stdin_to_stdout(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("token=ghp_FIXTUREabcdefgh"))
    monkeypatch.setattr(sys, "argv", ["_sanitize_diag.py"])
    assert sd.main() == 0
    out = capsys.readouterr().out
    assert "<redacted-gh-pat>" in out
    assert "ghp_FIXTUREabcdefgh" not in out


def test_cli_in_place_rewrites_file(tmp_path: Path) -> None:
    p = tmp_path / "log.txt"
    p.write_text("api_key=sk-ant-fixture12345678 trailing", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SANITIZE_PY), str(p), "--in-place"],
        check=True,
        capture_output=True,
    )
    assert result.returncode == 0
    rewritten = p.read_text(encoding="utf-8")
    assert "<redacted-anthropic-key>" in rewritten
    assert "fixture12345678" not in rewritten


def test_cli_in_place_requires_file_arg(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SANITIZE_PY), "--in-place"],
        capture_output=True,
    )
    assert result.returncode == 2
    assert b"--in-place requires" in result.stderr
