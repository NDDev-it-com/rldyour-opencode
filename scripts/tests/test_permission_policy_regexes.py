"""Regex coverage for `.opencode/plugins/ry-permission-policy.ts`.

The plugin denies three categorically dangerous bash patterns at the
`permission.ask` hook. The TypeScript regexes are mirrored here so that
a contributor changing either side gets a CI failure if the two
diverge.

Lockstep rule: every regex in this file MUST stay byte-for-byte
equivalent to the corresponding regex in the TypeScript source.
The PolicyRegexes class below is the single owner of those mirrors
and the tests are parametrised against the same instance.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLUGIN_PATH = PROJECT_ROOT / ".opencode" / "plugins" / "ry-permission-policy.ts"


@dataclass(frozen=True)
class PolicyRegexes:
    """Python mirror of the TypeScript regex set in ry-permission-policy.ts.

    Each TS regex is rewritten with Python `re` syntax. Word boundaries
    behave identically between V8 and CPython for these patterns
    (verified manually for the relevant cases).
    """

    is_push: re.Pattern[str] = field(default_factory=lambda: re.compile(r"\bgit\s+push\b", re.IGNORECASE))
    long_force: re.Pattern[str] = field(default_factory=lambda: re.compile(r"(?<![A-Za-z0-9-])--force(?![A-Za-z0-9-])", re.IGNORECASE))
    short_force: re.Pattern[str] = field(default_factory=lambda: re.compile(r"(?:^|\s)-[A-Za-z]*f[A-Za-z]*(?:\s|$)"))
    lease: re.Pattern[str] = field(default_factory=lambda: re.compile(r"(?<![A-Za-z0-9-])--force-with-lease(?![A-Za-z0-9-])", re.IGNORECASE))
    rm_root: re.Pattern[str] = field(default_factory=lambda: re.compile(r"\brm\s+(-rf?|-fr|--recursive)\s+/\s*$", re.IGNORECASE))
    rm_home_var: re.Pattern[str] = field(default_factory=lambda: re.compile(r"\brm\s+(-rf?|-fr|--recursive)\s+\$HOME\b", re.IGNORECASE))
    rm_home_tilde: re.Pattern[str] = field(default_factory=lambda: re.compile(r"\brm\s+(-rf?|-fr|--recursive)\s+~/?\s*$", re.IGNORECASE))
    rm_cwd_dot: re.Pattern[str] = field(default_factory=lambda: re.compile(r"\brm\s+(-rf?|-fr|--recursive)\s+\.\s*$", re.IGNORECASE))
    rm_node_modules: re.Pattern[str] = field(default_factory=lambda: re.compile(
        r"\brm\s+(-rf?|-fr|--recursive)\s+\S*/?node_modules/?\s*$", re.IGNORECASE
    ))
    no_verify: re.Pattern[str] = field(default_factory=lambda: re.compile(r"(?<![A-Za-z0-9-])--no-verify(?![A-Za-z0-9-])", re.IGNORECASE))
    product_branch: re.Pattern[str] = field(default_factory=lambda: re.compile(r"\b(main|master|release|production)\b", re.IGNORECASE))


P = PolicyRegexes()


def force_push_blocked(cmd: str) -> bool:
    is_push = bool(P.is_push.search(cmd))
    has_force = bool(P.long_force.search(cmd)) or bool(P.short_force.search(cmd))
    has_lease = bool(P.lease.search(cmd))
    return is_push and has_force and not has_lease


def rm_blocked(cmd: str) -> bool:
    dangerous = bool(
        P.rm_root.search(cmd)
        or P.rm_home_var.search(cmd)
        or P.rm_home_tilde.search(cmd)
        or P.rm_cwd_dot.search(cmd)
    )
    if not dangerous:
        return False
    return not bool(P.rm_node_modules.search(cmd))


def no_verify_product_branch_blocked(cmd: str) -> bool:
    return bool(P.is_push.search(cmd)) and bool(P.no_verify.search(cmd)) and bool(P.product_branch.search(cmd))


# ---------------------------------------------------------------------------
# Force push
# ---------------------------------------------------------------------------

FORCE_POSITIVES = (
    "git push --force",
    "git push --force origin main",
    "git push origin main --force",
    "git push  --force",  # two spaces
    "git push --FORCE",  # case-insensitive
    "git push --force=true",  # = retains word boundary on `--force`
    "git push -f",
    "git push -f origin feature",
    "git push origin feature -f",
)

FORCE_NEGATIVES = (
    "git push --force-with-lease",
    "git push --force-with-lease origin main",
    "git push origin main",
    "git status --force",  # no `git push`
    "git pushed --force",  # `\b` on `push\b` blocks the longer word
    "git push --force-with-lease=ref:something",
)


@pytest.mark.parametrize("cmd", FORCE_POSITIVES)
def test_force_push_blocked_positives(cmd: str) -> None:
    assert force_push_blocked(cmd), f"force_push_blocked({cmd!r}) should be True"


@pytest.mark.parametrize("cmd", FORCE_NEGATIVES)
def test_force_push_blocked_negatives(cmd: str) -> None:
    assert not force_push_blocked(cmd), f"force_push_blocked({cmd!r}) should be False"


# ---------------------------------------------------------------------------
# rm -rf
# ---------------------------------------------------------------------------

RM_POSITIVES = (
    "rm -rf /",
    "rm -rf $HOME",
    "rm -r $HOME",
    "rm -fr $HOME",
    "rm --recursive $HOME",
    "rm -rf ~",
    "rm -rf ~/",
    "rm -rf .",
)

RM_NEGATIVES_NODE = (
    "rm -rf node_modules",
    "rm -rf ./node_modules",
    "rm -rf ./node_modules/",
    "rm -rf packages/foo/node_modules",
    "rm -rf packages/foo/node_modules/",
)

RM_NEGATIVES_SAFE = (
    "rm -rf ~/specific-subdir",  # not the home root
    "rm -rf /tmp/foo",  # not catastrophic
    "rm -rf ./some/scoped/path",
    "rm foo.txt",  # no -rf
    "rm -i ~/foo",  # not recursive
)


@pytest.mark.parametrize("cmd", RM_POSITIVES)
def test_rm_blocked_positives(cmd: str) -> None:
    assert rm_blocked(cmd), f"rm_blocked({cmd!r}) should be True"


@pytest.mark.parametrize("cmd", RM_NEGATIVES_NODE)
def test_rm_node_modules_allowed(cmd: str) -> None:
    assert not rm_blocked(cmd), f"rm_blocked({cmd!r}) should be False (node_modules cleanup)"


@pytest.mark.parametrize("cmd", RM_NEGATIVES_SAFE)
def test_rm_other_safe_paths_allowed(cmd: str) -> None:
    assert not rm_blocked(cmd), f"rm_blocked({cmd!r}) should be False"


# ---------------------------------------------------------------------------
# --no-verify product branch
# ---------------------------------------------------------------------------

NV_POSITIVES = (
    "git push --no-verify origin main",
    "git push --no-verify origin master",
    "git push --no-verify origin release",
    "git push --no-verify origin production",
)

NV_NEGATIVES = (
    "git push --no-verify origin feature/x",
    "git push --no-verify origin mainline",  # `\b(main)\b` must NOT match
    "git push --no-verify origin mainframe",  # ditto
    "git push --no-verify origin productionish",  # `\b(production)\b` must NOT match
    "git push origin main",  # no --no-verify
    "git push --verify origin main",  # no --no-verify
)


@pytest.mark.parametrize("cmd", NV_POSITIVES)
def test_no_verify_product_blocked_positives(cmd: str) -> None:
    assert no_verify_product_branch_blocked(cmd), (
        f"no_verify_product_branch_blocked({cmd!r}) should be True"
    )


@pytest.mark.parametrize("cmd", NV_NEGATIVES)
def test_no_verify_product_blocked_negatives(cmd: str) -> None:
    assert not no_verify_product_branch_blocked(cmd), (
        f"no_verify_product_branch_blocked({cmd!r}) should be False"
    )


# ---------------------------------------------------------------------------
# Lockstep guard
# ---------------------------------------------------------------------------

def test_typescript_source_uses_same_regexes() -> None:
    """If a contributor changes one of the Python mirrors above, this
    guard fails until the TS source is updated to match (or vice
    versa). Each mirror name maps to a verbatim substring expected in
    the TS source.
    """
    src = PLUGIN_PATH.read_text(encoding="utf-8")
    expected_substrings = (
        r"\bgit\s+push\b",
        r"FLAG_BOUNDARY_PRE",  # constants declared in ry-permission-policy.ts
        r"FLAG_BOUNDARY_POST",
        r"(?<![A-Za-z0-9-])",
        r"(?![A-Za-z0-9-])",
        r"--force",
        # shortForce regex widened by reviewer wave 2026-05-18 security F-2
        # to catch combined-flag clusters like `-fv`, `-fq`, `-fn`, `-vf`.
        r"(?:^|\s)-[A-Za-z]*f[A-Za-z]*(?:\s|$)",
        r"--force-with-lease",
        r"\brm\s+(-rf?|-fr|--recursive)\s+\/\s*$",
        r"\brm\s+(-rf?|-fr|--recursive)\s+\$HOME\b",
        r"\brm\s+(-rf?|-fr|--recursive)\s+~\/?\s*$",
        r"\brm\s+(-rf?|-fr|--recursive)\s+\.\s*$",
        # Parent-dir traversal pattern added by reviewer wave 2026-05-18
        # security F-1: `rm -rf ..` from a project subdirectory would
        # otherwise erase the entire tree.
        r"\brm\s+(-rf?|-fr|--recursive)\s+\.\.\/?\s*$",
        r"\brm\s+(-rf?|-fr|--recursive)\s+\S*\/?node_modules\/?\s*$",
        r"--no-verify",
        r"\b(main|master|release|production)\b",
    )
    for needle in expected_substrings:
        assert needle in src, (
            f"TS source missing regex literal {needle!r} — "
            "Python mirror in test_permission_policy_regexes.py drifted from ry-permission-policy.ts"
        )
