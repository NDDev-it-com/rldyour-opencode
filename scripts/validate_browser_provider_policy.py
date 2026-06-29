#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = (
    "@playwright/" + "mcp",
    "Playwright " + "MCP",
    "playwright_" + "*",
)
REQUIRED_SKILLS = {
    "browser-tool-routing",
    "browser-validation",
    "browser-debug",
    "playwright-cli-validation",
    "webwright-task",
    "visual-diff-review",
}
SAFE_CHROME_ARGS = {"--headless", "--isolated", "--no-usage-statistics", "--no-performance-crux"}


class Failure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def text_files() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if ".serena" in path.parts and "cache" in path.parts:
            continue
        if path.name == "CHANGELOG.md" or "decisions" in path.parts:
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".zip", ".pyc"}:
            continue
        paths.append(path)
    return paths


def validate() -> None:
    hits: list[str] = []
    for path in text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in FORBIDDEN:
                if pattern in line:
                    hits.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")
    require(not hits, "retired browser MCP references remain:\n" + "\n".join(hits[:40]))

    config = json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))
    mcp = config.get("mcp") or {}
    require("playwright" not in mcp, "playwright must not be an active MCP server")
    chrome = mcp.get("chrome-devtools") or {}
    require(bool(chrome), "chrome-devtools MCP server is required")
    command = [str(item) for item in chrome.get("command") or []]
    require(set(command) >= SAFE_CHROME_ARGS, "chrome-devtools MCP args must keep safe defaults")

    for skill in REQUIRED_SKILLS:
        path = ROOT / ".opencode/skills" / skill / "SKILL.md"
        require(path.is_file(), f"missing browser skill: {skill}")
    contract = json.loads((ROOT / "references/rldyour-contract.json").read_text(encoding="utf-8"))
    support = str((contract.get("browser_providers") or {}).get("webwright_support") or "")
    require("NOT_PROVEN" in support and "adapter-owned-cli-wrapper" in support, "OpenCode Webwright support must be adapter-owned and NOT_PROVEN upstream-native")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OpenCode browser provider policy.")
    parser.add_argument("--strict", action="store_true")
    parser.parse_args()
    try:
        validate()
    except Failure as exc:
        print(f"ERROR: {exc}", flush=True)
        return 1
    print("ok: OpenCode browser provider policy validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
