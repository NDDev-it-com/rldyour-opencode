"""Sanitizer tests for ry-command-audit.ts.

The plugin runs in Bun and we cannot import the TypeScript directly,
so this suite mirrors the sanitizer regex set in pure Python and
exercises every credential pattern + fallback threshold. If the regex
set drifts between this file and the plugin, update both — the file
docstrings of each test name the matching plugin pattern.
"""
from __future__ import annotations

import re

# Mirror of ry-command-audit.ts sanitizeArgs() patterns. Update both
# when the plugin sanitizer regex set changes.
PATTERNS: list[tuple[str, str]] = [
    (r"sk-[A-Za-z0-9_\-]{8,}", "<redacted-api-key>"),
    (r"ghp_[A-Za-z0-9]{8,}", "<redacted-pat>"),
    (r"ghs_[A-Za-z0-9]{8,}", "<redacted-gh-server-token>"),
    (r"gho_[A-Za-z0-9]{8,}", "<redacted-gh-oauth>"),
    (r"glpat-[A-Za-z0-9_\-]{8,}", "<redacted-gitlab-pat>"),
    (r"AKIA[0-9A-Z]{16}", "<redacted-aws-access-key>"),
    (r"ASIA[0-9A-Z]{16}", "<redacted-aws-session-key>"),
    (r"xox[abprs]-[A-Za-z0-9\-]+", "<redacted-slack-token>"),
    (r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}", "<redacted-jwt>"),
    (
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----",
        "<redacted-pem>",
    ),
    (r"[A-Za-z0-9_\-]{32,}", "<redacted-long-token>"),
]

MAX_LINE_LEN = 280


def sanitize(raw: str) -> str:
    out = raw
    for pat, repl in PATTERNS:
        out = re.sub(pat, repl, out)
    return out[:MAX_LINE_LEN]


# ---------- known credential prefixes ----------


def test_openai_anthropic_key_redacted() -> None:
    assert "<redacted-api-key>" in sanitize("token=sk-1234567890abcdef1234")


def test_github_classic_pat_redacted() -> None:
    assert "<redacted-pat>" in sanitize("pat=ghp_abcdefghij1234567890")


def test_github_server_to_server_redacted() -> None:
    assert "<redacted-gh-server-token>" in sanitize("token=ghs_abcdefghij1234567890")


def test_github_oauth_redacted() -> None:
    assert "<redacted-gh-oauth>" in sanitize("token=gho_abcdefghij1234567890")


def test_gitlab_pat_redacted() -> None:
    assert "<redacted-gitlab-pat>" in sanitize("token=glpat-abcdefghij1234")


def test_aws_access_key_id_redacted() -> None:
    assert "<redacted-aws-access-key>" in sanitize("key=AKIA1234567890ABCDEF")


def test_aws_session_key_id_redacted() -> None:
    assert "<redacted-aws-session-key>" in sanitize("key=ASIA1234567890ABCDEF")


def test_slack_bot_token_redacted() -> None:
    assert "<redacted-slack-token>" in sanitize("token=xoxb-12345-abcdef-XYZ")


def test_slack_user_token_redacted() -> None:
    assert "<redacted-slack-token>" in sanitize("token=xoxp-12345-abcdef-XYZ")


def test_jwt_three_segment_redacted() -> None:
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0"
        ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    assert "<redacted-jwt>" in sanitize(f"auth={jwt}")


def test_pem_private_key_redacted() -> None:
    pem = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA1234567890abcdef\n"
        "abcdefghijklmnopqrstuvwxyz1234\n"
        "-----END RSA PRIVATE KEY-----"
    )
    assert "<redacted-pem>" in sanitize(f"key={pem}")


# ---------- generic-length threshold (verification reviewer finding) ----------


def test_aws_secret_key_40chars_redacted() -> None:
    """40-char AWS Secret Access Key (no AKIA prefix) must hit the
    generic-length redactor at threshold 32+. Regression for the
    previous `> 48` bug that left 40-char tokens in the clear."""
    secret = "abcDEF1234567890abcDEF1234567890abcDEF12"  # 40 chars
    assert len(secret) == 40
    assert "<redacted-long-token>" in sanitize(f"key={secret}")


def test_token_32chars_redacted() -> None:
    token = "a" * 32
    assert "<redacted-long-token>" in sanitize(f"t={token}")


def test_token_31chars_not_redacted() -> None:
    """31-char token is below threshold and survives — accepted false-negative."""
    token = "a" * 31
    assert token in sanitize(f"t={token}")


def test_token_49chars_redacted() -> None:
    token = "x" * 49
    assert "<redacted-long-token>" in sanitize(f"t={token}")


# ---------- truncation ----------


def test_output_truncated_to_280() -> None:
    raw = "a" * 1000
    result = sanitize(raw)
    assert len(result) <= MAX_LINE_LEN
