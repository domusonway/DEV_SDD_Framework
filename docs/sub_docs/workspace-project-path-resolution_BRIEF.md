# Workspace Project Path Resolution BRIEF

## Goal
DEV_SDD must support workspace-style active projects where `PROJECT` is a logical name and `PROJECT_PATH` points to the real project root, e.g. `projects/agentplatform_workspace/agentplatform`.

## Rules
- When `PROJECT_PATH` exists, all project context, docs, memory, sessions, challenges, plans, and generated document paths must resolve under `PROJECT_PATH`.
- `PROJECT` remains the display/logical project name and must not be blindly expanded as `projects/<PROJECT>` when `PROJECT_PATH` is configured.
- Explicit absolute or relative project paths still override active project configuration.
- If a command receives the active `PROJECT` name explicitly and `PROJECT_PATH` is configured, it should resolve to `PROJECT_PATH`.

## Acceptance
- `start-work` with no project uses `PROJECT_PATH` for workspace projects.
- `doc-template` suggestions for active or explicit project names use `PROJECT_PATH`.
- `session-snapshot` writes under `PROJECT_PATH/memory/sessions`, not `projects/<PROJECT>/memory/sessions`.
- `challenge-gate --project <PROJECT>` reports challenge records under `PROJECT_PATH/memory/challenges` when `PROJECT_PATH` is configured.
- Startup and memory rules document the path resolution precedence.
