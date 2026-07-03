<!-- Memory Metadata
Last updated: 2026-05-22
Last commit: 869dac43071c53d4b93d06ed006d873fb5f66b13 chore(release): opencode 1.7.11 (other)
Scope: release readiness, versioning, and artifact hygiene
Area: RELEASE
-->

# Release Validation

## Scope
release readiness, versioning, and artifact hygiene

## Current source of truth
- `path:VERSION`
- `path:CHANGELOG.md`
- `path:.github/workflows/release.yml`

## Last verified
- date: 2026-05-22
- commit: `869dac43071c53d4b93d06ed006d873fb5f66b13`
- checked by: Codex ry-start memory taxonomy sync

## Facts
- Current rldyour-opencode adapter VERSION is `1.7.11`; the release workflow publishes the matching numeric GitHub Release tag at the released commit.
- Release memories record numeric versioning, tags, CI gates, and clean artifact hygiene.

## Evidence
- `commit:869dac43071c53d4b93d06ed006d873fb5f66b13`
- `path:VERSION`
- `path:CHANGELOG.md`
- `path:.github/workflows/release.yml`

## Known pitfalls
- Treat this memory as derived context. Current code, configuration, runtime output, and GitHub state override stale memory text.

## Update policy
Update after verified changes to the referenced source-of-truth files.

## Delete / merge policy
- Delete or merge only when the referenced source-of-truth files no longer support this memory and the replacement memory preserves the durable facts.
