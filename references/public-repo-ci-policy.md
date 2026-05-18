# Public Repository CI/CD Policy

This file is loaded directly by OpenCode through `opencode.json.instructions`.
It exists because CI/CD behavior is a runtime policy, not only a repository doc.

## Rule

Public repositories must use automatic CI/CD by default. Private repositories
remain explicit/manual by default.

## Visibility Gate

Treat a repository as public when any verified source says it is public:

- GitHub API / CLI reports `isPrivate: false` for the current `origin`.
- GitHub Actions context reports `github.event.repository.private == false`.
- The owner explicitly states the repository is public in the current task.

If visibility cannot be verified, keep the private/manual default and say why.

## OpenCode Behavior

When the repository is public:

- Existing GitHub Actions workflows are considered the default verification
  surface after meaningful code, config, docs, workflow, release, or package
  changes.
- `/ry-start`, `/ry-sync`, and `/ry-deploy` must not stop at local checks after
  a push or tag. They must verify the automatically triggered GitHub Actions
  runs for the same HEAD/tag and report their run IDs.
- If a required public-release or readiness workflow is `workflow_dispatch` /
  schedule / release-only and did not run for the current public-repo change,
  triggering that existing workflow with `gh workflow run` is allowed without a
  separate confirmation, then the agent must wait for completion.
- Do not create, edit, delete, enable, or disable workflows, branch protection,
  repository rulesets, environments, secrets, variables, or deployment targets
  unless the owner explicitly requested that mutation in the current task.

When the repository is private:

- Triggering CI/CD workflows remains an owner-restricted mutation unless the
  owner explicitly requests it in the current task.
- Local validation may be sufficient when remote workflow execution is not
  requested or not available.

## What Stays Manual

This policy does not change OpenCode `share`. `share: "manual"` controls
session sharing, not CI/CD. Keep it manual unless the owner explicitly asks to
change OpenCode session-sharing behavior.
