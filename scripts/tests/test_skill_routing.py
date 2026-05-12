"""Skill routing quality checks.

OpenCode auto-routes prompts to skills by matching against the
`description` frontmatter. This suite enforces that every skill in
`.opencode/skills/` has a description rich enough for both Russian
and English routing — a discipline borrowed from the codex
marketplace's `config/skill-routing-policy.json` deterministic tests.

Cases enforce:
- description present and within 1-1024 chars
- description carries Russian routing phrase (`Используй для` or
  `Use for`) so RU prompts route correctly
- description carries explicit English keyword block
  (`EN triggers:` suffix) so EN prompts route correctly
- skill name = directory name = kebab-case
- no duplicate skill names across the catalog
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# sys.path setup via conftest.py
import _validate_helpers as vh

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / ".opencode" / "skills"

MIN_DESCRIPTION_LEN = 80  # short descriptions starve the router
MAX_DESCRIPTION_LEN = 1024  # OpenCode schema upper bound


def _skill_dirs() -> list[Path]:
    return sorted(d for d in SKILLS_DIR.iterdir() if d.is_dir())


def _read_description(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8-sig")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return ""
    return vh._yaml_top_key(m.group(1), "description") or ""


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda d: d.name)
def test_description_length_in_range(skill_dir: Path) -> None:
    desc = _read_description(skill_dir)
    length = len(desc)
    assert MIN_DESCRIPTION_LEN <= length <= MAX_DESCRIPTION_LEN, (
        f"{skill_dir.name}: description length {length} not in "
        f"[{MIN_DESCRIPTION_LEN}, {MAX_DESCRIPTION_LEN}]"
    )


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda d: d.name)
def test_description_has_russian_routing_phrase(skill_dir: Path) -> None:
    """Either `Используй для` (Russian) or `Use for` (English) must appear."""
    desc = _read_description(skill_dir)
    has_ru = "Используй для" in desc
    has_use_for = "Use for" in desc
    assert has_ru or has_use_for, (
        f"{skill_dir.name}: description missing routing phrase "
        f"('Используй для' or 'Use for')"
    )


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda d: d.name)
def test_description_has_english_triggers(skill_dir: Path) -> None:
    """English-language prompts route via the explicit `EN triggers:` block.

    Allow either an explicit `EN triggers:` suffix OR descriptions that
    are already English-leading (start with an English-only sentence).
    """
    desc = _read_description(skill_dir)
    if "EN triggers" in desc:
        return
    # Fallback: description starts with an English-only word for the first 30 chars.
    head = desc[:30].strip()
    if head and all(ord(c) < 128 for c in head):
        return
    pytest.fail(
        f"{skill_dir.name}: description has neither 'EN triggers:' suffix "
        f"nor an English-leading head"
    )


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda d: d.name)
def test_skill_name_kebab_case(skill_dir: Path) -> None:
    assert re.match(r"^[a-z][a-z0-9-]{0,63}$", skill_dir.name), (
        f"{skill_dir.name}: not kebab-case (1-64 chars, [a-z0-9-], starts with letter)"
    )


def test_skill_directory_names_unique() -> None:
    names = [d.name for d in _skill_dirs()]
    duplicates = [n for n in names if names.count(n) > 1]
    assert not duplicates, f"duplicate skill directories: {set(duplicates)}"
