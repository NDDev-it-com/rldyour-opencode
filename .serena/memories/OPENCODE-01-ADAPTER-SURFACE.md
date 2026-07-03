<!-- Memory Metadata
Last updated: 2026-05-22
Last commit: d93a558050d54a80e578035d0e1627385ec7c1e4 test(runtime): stabilize opencode debug resolve smoke
Scope: OpenCode adapter implementation surface
Area: OPENCODE
-->

# OpenCode Adapter Surface

## Scope
OpenCode adapter implementation surface

## Current source of truth
- `path:opencode.json`
- `path:references/rldyour-contract.json`

## Last verified
- date: 2026-05-22
- commit: `d93a558050d54a80e578035d0e1627385ec7c1e4`
- checked by: Codex ry-start memory taxonomy sync

## Facts
- OpenCode memories describe opencode.json, local plugins, commands, skills, agents, permissions, MCP, and LSP.

## Evidence
- `commit:d93a558050d54a80e578035d0e1627385ec7c1e4`
- `path:opencode.json`
- `path:references/rldyour-contract.json`

## Known pitfalls
- Treat this memory as derived context. Current code, configuration, runtime output, and GitHub state override stale memory text.

## Update policy
Update after verified changes to the referenced source-of-truth files.

## Delete / merge policy
- Delete or merge only when the referenced source-of-truth files no longer support this memory and the replacement memory preserves the durable facts.
