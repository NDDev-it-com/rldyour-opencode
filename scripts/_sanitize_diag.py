#!/usr/bin/env python3
"""Credential-pattern stripper for diagnostic bundles.

Reads stdin (or a file passed as the first positional argument) and
writes a sanitised copy to stdout (or the file path passed as `--in-place`).
Strips every credential-shaped substring before it lands in
`diagnostics/`. Mirrors the regex set in `.opencode/plugins/ry-command-audit.ts`
(`sanitizeArgs`) so both surfaces share the same coverage.

The fallback `[A-Za-z0-9_\\-]{32,}` rule is *not* enabled here — diagnostic
bundles routinely contain SHA-1 (40 hex), commit subjects, dependency
pin strings (e.g. `serena-agent==1.3.0`), and other opaque-looking but
non-secret strings that would all be false-positive redacted. The
specific-prefix patterns below already cover the well-known API key
shapes that `opencode debug config` would substitute into the output.

Exit codes:
  0  Success.
  2  Bad input.

Usage:
    python3 scripts/_sanitize_diag.py < input.txt > output.txt
    python3 scripts/_sanitize_diag.py path/to/file --in-place
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Pattern ordering rule: more-specific prefixes MUST run before less-specific
# ones (`ctx7sk-` before `sk-`, `sk-ant-` / `sk-proj-` before `sk-`). The
# generic `sk-` pattern also uses a negative-lookbehind to refuse a match
# whose preceding char is a word/dash char — that prevents `sk-` matching
# *inside* a longer compound like `ctx7sk-...` even if the order regresses.
# Kept in lockstep with `.opencode/plugins/ry-command-audit.ts::sanitizeArgs`
# plus a Context7 entry for the `ctx7sk-` keys that `opencode debug config`
# substitutes into its output.
PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Vendor-specific prefixes first.
    (re.compile(r"ctx7sk-[A-Za-z0-9_\-]{8,}"), "<redacted-context7-key>"),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"), "<redacted-anthropic-key>"),
    (re.compile(r"sk-proj-[A-Za-z0-9_\-]{8,}"), "<redacted-openai-project-key>"),
    # Generic `sk-...` with a word-boundary lookbehind so it cannot match a
    # substring of a longer compound (`ctx7sk-...` etc.) if the order ever
    # regresses. Stricter than the TS sibling — defensible because the
    # diagnostic bundle path is more sensitive than the audit-log path.
    (re.compile(r"(?<![A-Za-z0-9_\-])sk-[A-Za-z0-9_\-]{8,}"), "<redacted-api-key>"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "<redacted-gh-fine-grained-pat>"),
    (re.compile(r"ghp_[A-Za-z0-9]{8,}"), "<redacted-gh-pat>"),
    (re.compile(r"ghs_[A-Za-z0-9]{8,}"), "<redacted-gh-server-token>"),
    (re.compile(r"gho_[A-Za-z0-9]{8,}"), "<redacted-gh-oauth>"),
    (re.compile(r"glpat-[A-Za-z0-9_\-]{8,}"), "<redacted-gitlab-pat>"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "<redacted-aws-access-key>"),
    (re.compile(r"ASIA[0-9A-Z]{16}"), "<redacted-aws-session-key>"),
    (re.compile(r"xox[abprs]-[A-Za-z0-9\-]+"), "<redacted-slack-token>"),
    (
        re.compile(r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}"),
        "<redacted-jwt>",
    ),
    (
        re.compile(
            r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----"
        ),
        "<redacted-pem>",
    ),
)


def sanitize(text: str) -> str:
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("file", nargs="?", help="input file (defaults to stdin)")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="rewrite the input file with its sanitised contents (requires `file`)",
    )
    args = parser.parse_args()

    if args.in_place and not args.file:
        print("--in-place requires a file path", file=sys.stderr)
        return 2

    if args.file:
        path = Path(args.file)
        raw = path.read_text(encoding="utf-8", errors="replace")
        clean = sanitize(raw)
        if args.in_place:
            path.write_text(clean, encoding="utf-8")
        else:
            sys.stdout.write(clean)
    else:
        sys.stdout.write(sanitize(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
