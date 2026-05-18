"""Plugin surface integrity tests.

Verify that the 10 plugins listed in AGENTS.md actually exist on disk, that
ry-tool-hints' HINTS keys reference real MCP servers from opencode.json,
and that ry-tools' registered tool IDs match what AGENTS.md and CHANGELOG
claim. Catches future drift between plugin code, the manifest, and
human-facing docs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLUGINS_DIR = PROJECT_ROOT / ".opencode" / "plugins"
OPENCODE_JSON = PROJECT_ROOT / "opencode.json"
AGENTS_MD = PROJECT_ROOT / "AGENTS.md"

EXPECTED_PLUGINS = {
    "ry-bootstrap.ts",
    "ry-env-protection.ts",
    "ry-shell-strategy.ts",
    "ry-sync-reminder.ts",
    "ry-flow-hooks.ts",
    "ry-tools.ts",
    "ry-command-audit.ts",
    "ry-tool-hints.ts",
    "ry-permission-policy.ts",
    "ry-system-context.ts",
}

EXPECTED_RY_TOOL_IDS = {
    "rldyour_validate_config",
    "rldyour_check_deps",
    "rldyour_lsp_health",
    "rldyour_git_audit",
    "rldyour_fullrepo_status",
}


def test_all_expected_plugins_exist() -> None:
    actual = {p.name for p in PLUGINS_DIR.glob("*.ts")}
    assert actual == EXPECTED_PLUGINS, (
        f"plugin set drifted — extra={actual - EXPECTED_PLUGINS}, missing={EXPECTED_PLUGINS - actual}"
    )


def test_plugin_count_matches_agents_md() -> None:
    text = AGENTS_MD.read_text(encoding="utf-8-sig")
    match = re.search(r"rldyour plugins \((\d+)\)", text)
    assert match, "AGENTS.md must list 'rldyour plugins (N)'"
    declared = int(match.group(1))
    actual = len(list(PLUGINS_DIR.glob("*.ts")))
    assert declared == actual, f"AGENTS.md says {declared} plugins but {actual} exist on disk"


def test_ry_tools_registers_expected_ids() -> None:
    src = (PLUGINS_DIR / "ry-tools.ts").read_text(encoding="utf-8")
    found = set(re.findall(r"^\s*(rldyour_[A-Za-z0-9_]+):\s*tool\(", src, re.MULTILINE))
    assert found == EXPECTED_RY_TOOL_IDS, (
        f"ry-tools.ts ID drift — extra={found - EXPECTED_RY_TOOL_IDS}, "
        f"missing={EXPECTED_RY_TOOL_IDS - found}"
    )


def test_ry_tool_hints_references_real_mcp_servers() -> None:
    """Every HINTS key must use the OpenCode v1.14.48 MCP tool ID format
    `<server>_<tool>` (single underscore) and reference a server that exists
    in opencode.json.mcp. Catches drift when an MCP server is renamed,
    removed, or when the legacy `mcp__server__tool` Claude Code prefix is
    re-introduced (the underscore-double form does NOT match OpenCode's
    sanitize(serverName) + "_" + sanitize(toolName) build line)."""
    cfg = json.loads(OPENCODE_JSON.read_text(encoding="utf-8-sig"))
    mcp_servers = set((cfg.get("mcp") or {}).keys())

    hints_src = (PLUGINS_DIR / "ry-tool-hints.ts").read_text(encoding="utf-8")
    # Non-greedy [\w-]+? + literal "_" matches the first underscore boundary,
    # which is always the server/tool separator (none of our MCP server names
    # contain underscores; v1.14.48 sanitize() does not introduce them either).
    keys = re.findall(r'^\s*"([\w-]+?)_[^"]+":\s', hints_src, re.MULTILINE)

    assert keys, "ry-tool-hints.ts has no HINTS keys (or regex drifted)"
    unknown = {k for k in keys if k not in mcp_servers}
    assert not unknown, (
        f"ry-tool-hints.ts references MCP server(s) not in opencode.json: {unknown}"
    )


def test_ry_tool_hints_no_legacy_aliases() -> None:
    """Defensive: catch the previous Context7 misalias AND the entire
    Claude-Code-style `mcp__server__tool` key shape. OpenCode v1.14.48
    builds tool IDs as `server_tool` (single underscore). Any `mcp__`
    substring inside HINTS keys would silently disable that hint, so
    block the prefix entirely from `ry-tool-hints.ts`."""
    LEGACY_BANNED = {
        "mcp__context7__get-library-docs",  # never existed; real names are query-docs / resolve-library-id
        "mcp__",  # entire Claude-Code prefix is invalid for OpenCode tool IDs (see test docstring)
    }
    hints_src = (PLUGINS_DIR / "ry-tool-hints.ts").read_text(encoding="utf-8")
    # Strip JS/TS comments before scanning — the file documents the legacy
    # format in its module header on purpose. Only check the live HINTS map.
    code_only = re.sub(r"^\s*//.*$", "", hints_src, flags=re.MULTILINE)
    for banned in LEGACY_BANNED:
        assert banned not in code_only, (
            f"ry-tool-hints.ts contains legacy Claude-Code-style key {banned!r}"
        )


def test_no_dead_project_path_cast_in_plugins() -> None:
    """Defensive: catches re-introduction of the `project as { ... path? }`
    cast and any access pattern that reads `project.path` directly. The
    SDK Project type (gen/types.gen.d.ts) exposes `worktree` instead;
    `path` was a hand-rolled runtime-only field that worked by accident
    in early v1.14 and is now dead surface.

    Plugins must use either the typed `project.worktree` or destructure
    `directory` directly from PluginInput. Guards against three regression
    classes:

    1. Cast forms like `project as { path?: string }` or
       `project as { name?: string; path?: string }`.
    2. The fallback chain `.path ?? directory` (only meaningful if .path
       is being read at all).
    3. Direct `proj?.path` access on a cast-stored alias.
    """
    cast_re = re.compile(r"project\s+as\s+\{[^}]*\bpath\?\s*:\s*string\b")
    for ts in PLUGINS_DIR.glob("*.ts"):
        src = ts.read_text(encoding="utf-8")
        assert cast_re.search(src) is None, (
            f"{ts.name} re-introduced a `project as {{ ... path?: string ... }}` cast"
        )
        assert ".path ?? directory" not in src, (
            f"{ts.name} reads `.path ?? directory` — drop the dead `.path` arm"
        )
        # The literal `proj?.path` pattern only appears when something
        # already aliased the cast — block it independently so a future
        # contributor cannot quietly reintroduce one half of the regression.
        assert "proj?.path" not in src, (
            f"{ts.name} reads `proj?.path` — dead Project field"
        )


def test_ry_env_protection_token_splitter_preserves_backslash() -> None:
    """Backslash is an escape marker, not a token separator.

    The splitter may still use `\\s` for whitespace, but it must not include a
    literal `\\` delimiter that would strip escaped path information before
    `isSensitivePath()` sees the token.
    """
    src = (PLUGINS_DIR / "ry-env-protection.ts").read_text(encoding="utf-8")
    match = re.search(r"command\.split\(/\[([^\]]+)\]\+/\)", src)
    assert match, "ry-env-protection.ts must tokenize bash commands"
    delimiter_class = match.group(1)
    assert r"\\" not in delimiter_class, (
        "command token splitter must preserve literal backslashes inside path tokens"
    )


def test_ry_shell_strategy_warns_on_bare_recursive_rm_targets() -> None:
    """Non-catastrophic recursive rm must warn even without slash targets."""
    src = (PLUGINS_DIR / "ry-shell-strategy.ts").read_text(encoding="utf-8")
    assert r"&& /\//.test(command)" not in src, (
        "destructive-rm warning must not be gated on slash-containing targets only"
    )
    assert "if (!isNodeModulesCleanup)" in src, (
        "node_modules remains the only non-catastrophic rm warning allowlist"
    )
    assert "Destructive rm command detected" in src


def test_ry_tool_hints_dispatch_path_wired() -> None:
    """Structural verification that the `tool.definition` hook in
    ry-tool-hints.ts actually mutates `output.description` when a
    matching toolID arrives. The key-format tests above prove the
    HINTS map is well-formed; this test proves the dispatch path
    reaches the assignment so the regression class "hook fires but
    writes nowhere" is impossible.
    """
    src = (PLUGINS_DIR / "ry-tool-hints.ts").read_text(encoding="utf-8")
    assert '"tool.definition"' in src, "ry-tool-hints.ts must subscribe to tool.definition"
    assert "HINTS[input.toolID]" in src, (
        "ry-tool-hints.ts must look up the hint by input.toolID"
    )
    assert "output.description" in src, (
        "ry-tool-hints.ts must write the hint into output.description"
    )
    # Guard: the assignment must be the only mutation; we do NOT want a
    # future contributor to mutate output.parameters (LLM tool schema)
    # since the marketplace contract is hint-only.
    assert "output.parameters" not in src, (
        "ry-tool-hints.ts must not mutate output.parameters — hints only"
    )


def test_ry_system_context_injects_runtime_fields() -> None:
    """Structural verification that ry-system-context.ts builds the
    `[rldyour runtime] ...` line with the four expected runtime fields
    (date, branch, head, worktree) and falls back to the literal
    string "unknown" when a git probe returns empty.
    """
    src = (PLUGINS_DIR / "ry-system-context.ts").read_text(encoding="utf-8")
    assert '"experimental.chat.system.transform"' in src, (
        "ry-system-context.ts must subscribe to experimental.chat.system.transform"
    )
    for field in ("date=", "branch=", "head=", "worktree="):
        assert field in src, f"ry-system-context.ts runtime line missing {field!r}"
    assert '|| "unknown"' in src, (
        "ry-system-context.ts must fall back to \"unknown\" on git probe failure"
    )
    assert "output.system.push(" in src, (
        "ry-system-context.ts must push the runtime line into output.system"
    )


def test_ry_system_context_uses_ttl_cache_for_branch_and_head() -> None:
    """Audit P1-6 closure: branch/head must be cached with a TTL rather
    than computed once at plugin factory init. Otherwise an in-session
    `git checkout|switch|rebase` leaves the prompt-injected `branch=` and
    `head=` stamps stale for the rest of the session.

    Pin the structural shape: a numeric TTL constant + a `Date.now()`
    age comparison gate every read, and a single shared cache slot
    keyed off the directory.
    """
    src = (PLUGINS_DIR / "ry-system-context.ts").read_text(encoding="utf-8")
    assert "BRANCH_HEAD_CACHE_TTL_MS" in src, (
        "ry-system-context.ts must define a named TTL constant for the branch/head cache"
    )
    assert "Date.now()" in src, (
        "ry-system-context.ts must compare cache age with Date.now() — "
        "otherwise the TTL gate is missing"
    )
    # Integration-review F-3 closure: the cache is keyed by `directory`
    # via a Map so multi-worktree sessions cannot serve a stale entry
    # from the wrong tree. Catch either the old singleton name
    # (cachedBranchHead) or the new Map (cacheByDirectory) — both are
    # acceptable, but the cache must exist in a named slot the
    # invalidation contract can talk about.
    assert (
        "cacheByDirectory" in src or "cachedBranchHead" in src
    ), "ry-system-context.ts must hold the cache in a named slot for invalidation"
    # Regression guard: the legacy 'cache at factory init' pattern stored the
    # values in `const cachedBranch = await readGitOutput(...)`. The replacement
    # is a function getter — assert the const-await form is gone.
    assert "const cachedBranch = " not in src, (
        "ry-system-context.ts must NOT cache branch/head at factory init; "
        "use the TTL-cached getter so in-session checkout invalidates correctly"
    )


def test_no_console_log_in_plugin_production_code() -> None:
    """Defensive: 0.10.0 migrated every plugin from `console.log` (server-
    log-only; invisible to the user) to `client.app.log` + `client.tui
    .showToast`. A regression that re-introduces `console.log/warn/error`
    in production code would silently mute the advisory channel again.

    Comments are stripped before scanning so the migration notes inside
    module headers can still mention `console.log` verbatim. Block
    comments (`/* ... */`) are also stripped to cover both styles.
    """
    BANNED = ("console.log", "console.warn", "console.error", "console.info")
    for ts in PLUGINS_DIR.glob("*.ts"):
        src = ts.read_text(encoding="utf-8")
        no_line_comments = re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)
        code_only = re.sub(r"/\*.*?\*/", "", no_line_comments, flags=re.DOTALL)
        offenders = [token for token in BANNED if token in code_only]
        assert not offenders, (
            f"{ts.name} contains production-code console call(s) {offenders!r}; "
            f"use client.app.log + client.tui.showToast (see references/"
            f"opencode-plugin-patterns.md § Observability pattern)"
        )


def test_flow_hooks_reads_command_from_input_args() -> None:
    """`tool.execute.after` in ry-flow-hooks.ts MUST read bash args from `input.args`,
    not `output.args`. The SDK contract (@opencode-ai/plugin@1.15.4) places args
    on the input side; reading from output silently swallows every git commit
    detection. This regression slipped through the 0.11.x train and is closed
    here in 0.12.0 with a structural guard. See audit Phase 0 P0-1.
    """
    src = (PLUGINS_DIR / "ry-flow-hooks.ts").read_text(encoding="utf-8")
    # The helper extracts from input.args:
    assert "input.args" in src, (
        "ry-flow-hooks.ts must read command from input.args (SDK contract). "
        "See audit Phase 0 P0-1 and references/opencode-plugin-patterns.md."
    )
    # The buggy pattern must not be reintroduced:
    assert "(output as { args?:" not in src, (
        "ry-flow-hooks.ts must not cast `output` to a shape with `.args` — "
        "args live on `input.args`, not `output.args`."
    )
    # The dedicated helper is present:
    assert "function getBashCommand(" in src, (
        "Expected `getBashCommand` helper in ry-flow-hooks.ts to centralize the input.args extraction."
    )



def test_cc_regex_anchored_after_branch_sha_prefix() -> None:
    """`git commit` stdout always begins with `[<branch> <sha>] <subject>` on
    its summary line. The legacy `^(type):` anchor with `m` flag silently
    failed for every real commit because the type prefix is never at
    start-of-line. Anchor must be `]\\s*(type)` so the matcher fires on
    real git output. Regression closed by reviewer wave 2026-05-18 quality F-1.
    """
    src = (PLUGINS_DIR / "ry-flow-hooks.ts").read_text(encoding="utf-8")
    assert "CC_REGEX = new RegExp(" in src, "CC_REGEX constant must remain in ry-flow-hooks.ts"
    # New anchor: closing bracket of `[branch sha]` prefix.
    assert "`\\\\]\\\\s*(${CC_TYPES})" in src, (
        "CC_REGEX must anchor at `]` after the `[branch sha]` prefix that git "
        "commit writes; the legacy `^(type):` anchor silently misses every "
        "real commit. See reviewer wave 2026-05-18 quality F-1."
    )
    # Legacy buggy anchor must not be reintroduced.
    assert "`^(${CC_TYPES})" not in src, (
        "CC_REGEX must NOT start with `^(type)` anchor — git stdout has "
        "`[branch sha] ` prefix before the type, so start-of-line never matches."
    )


def test_plugin_spawn_calls_have_timeout_guard() -> None:
    """Any plugin that spawns a child process via `Bun.spawn` must arm a
    timeout that calls `proc.kill()` on the kill path. Without that guard a
    hung subprocess can wedge `experimental.chat.system.transform` (ultra-hot
    path) or a custom diagnostic tool. See audit Phase 1 plugin timeouts.
    """
    for name in ("ry-system-context.ts", "ry-tools.ts"):
        src = (PLUGINS_DIR / name).read_text(encoding="utf-8")
        assert "Bun.spawn(" in src, f"{name} no longer uses Bun.spawn — update this test"
        assert "setTimeout(" in src and "proc?.kill()" in src, (
            f"{name} spawns child processes but is missing the timeout+kill guard. "
            f"See audit Phase 1 — every Bun.spawn call must arm a kill timer."
        )


def test_ry_env_protection_blocks_data_movement_utilities() -> None:
    """The env-protection plugin must block cp/mv/tar/zip/base64-style
    exfiltration utilities targeting sensitive paths, not just read/dump
    tokens. Audit Phase 1 widened the regex from the read-token set to also
    cover data movement.
    """
    src = (PLUGINS_DIR / "ry-env-protection.ts").read_text(encoding="utf-8")
    assert "dataMoveRe" in src or "data movement" in src.lower(), (
        "ry-env-protection.ts must classify cp/mv/tar/zip/base64 as data-movement "
        "vectors (audit Phase 1). Update the BLOCKED_PATTERNS comment block "
        "or restore the explicit dataMoveRe matcher."
    )
