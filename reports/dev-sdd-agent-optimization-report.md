# dev-sdd-agent-optimization report

## 1. Summary

The `dev-sdd-agent-optimization` work is complete and aligned around a single workflow contract: `INIT`, `REDEFINE`, `UPDATE_TODO`, `START_WORK`, and `FIX` now operate against project-scoped execution state with `docs/plan.json` as the execution source of truth.

This report is based on actual verified repository state inspected from the repo on disk, including `.sisyphus/plans/dev-sdd-agent-optimization.md`, `.sisyphus/notepads/dev-sdd-agent-optimization/{decisions,learnings}.md`, `README.md`, root `docs/*`, the five slash-command docs, the helper entrypoints under `.claude/tools/`, the workflow test cases under `skill-tests/cases/`, and the recorded final-wave approval sessions.

## 2. Completed changes

- Reframed root `docs/CONTEXT.md`, `docs/PLAN.md`, and `docs/TODO.md` as framework-level guidance only, instead of active-project runtime documents.
- Documented and reinforced that active project execution state lives under `projects/<PROJECT>/docs/*`, with `docs/plan.json` as the source of truth and project `PLAN.md` / `TODO.md` treated as derived or managed views.
- Aligned the project template and migration guidance so new and migrated projects follow the same ownership model.
- Added or updated the workflow helpers for `INIT`, `REDEFINE`, `UPDATE_TODO`, `START_WORK`, and `FIX`, and unified shared resolution/output behavior through `.claude/tools/workflow_cli_common.py`.
- Added workflow-focused regression coverage for helper contracts, migration guidance, drift prevention, and command-specific behavior.

## 3. Commands/helpers added or updated

- `INIT` — `.claude/commands/dev-sdd-init.md` and `.claude/tools/init/run.py`
  - Initializes or rebuilds project workflow scaffolding from project context.
  - Supports dry-run/confirmation behavior instead of silent overwrite.
- `REDEFINE` — `.claude/commands/dev-sdd-redefine.md` and `.claude/tools/redefine/run.py`
  - Re-propagates project workflow structure from project `docs/CONTEXT.md` into `docs/plan.json` and derived views.
  - `REDEFIND` remains compatibility-only; the canonical workflow name is `REDEFINE`.
- `UPDATE_TODO` — `.claude/commands/dev-sdd-update-todo.md` and `.claude/tools/update-todo/run.py`
  - Reconciles managed TODO content by stable task IDs sourced from `docs/plan.json`.
  - Preserves user notes and requires confirmation for unsafe overwrite/conflict scenarios.
- `START_WORK` — `.claude/commands/dev-sdd-start-work.md` and `.claude/tools/start-work/run.py`
  - Loads project/session/handoff context and reconciles TODO state without overriding plan order.
  - Uses `plan.json` precedence and reports warnings rather than reverting to markdown-first ownership.
- `FIX` — `.claude/commands/dev-sdd-fix.md` and `.claude/tools/fix/run.py`
  - Performs issue triage first, then returns exactly two option families: `minimal_change` and `comprehensive_change`.
  - It is an optioning workflow, not automatic patch application.
- Shared helper contract — `.claude/tools/workflow_cli_common.py`
  - Centralizes resolver behavior so the helper family follows a consistent `{status,message,data}` output envelope and path-resolution model.

## 4. Verification performed

The repository state supporting this report was verified by inspection of the shipped workflow surface and the recorded final verification wave:

- Plan and change record reviewed:
  - `.sisyphus/plans/dev-sdd-agent-optimization.md`
  - `.sisyphus/notepads/dev-sdd-agent-optimization/decisions.md`
  - `.sisyphus/notepads/dev-sdd-agent-optimization/learnings.md`
- Framework ownership and migration docs reviewed:
  - `docs/CONTEXT.md`
  - `README.md` migration and usage sections
- Command/helper surface confirmed present:
  - `.claude/commands/dev-sdd-{init,redefine,update-todo,start-work,fix}.md`
  - `.claude/tools/{init,redefine,update-todo,start-work,fix}/run.py`
- Workflow verification coverage confirmed present:
  - `skill-tests/cases/test_init_tool.py`
  - `skill-tests/cases/test_redefine_tool.py`
  - `skill-tests/cases/test_update_todo_tool.py`
  - `skill-tests/cases/test_start_work_tool.py`
  - `skill-tests/cases/test_fix_tool.py`
  - `skill-tests/cases/test_workflow_cli_contracts.py`
  - `skill-tests/cases/test_workflow_drift_guards.py`
  - `skill-tests/cases/test_workflow_migration_docs.py`
- Final-wave approval lines were read from recorded session history for F1-F4.

## 5. Final wave results

The final verification wave ended with `APPROVE` across F1-F4:

- **F1 — Plan Compliance Audit**
  - `Must Have [4/4] | Must NOT Have [4/4] | Tasks [13/13] | VERDICT: APPROVE`
- **F2 — Code Quality Review**
  - `Build PASS | Lint PASS | Tests 36 pass/0 fail | Files 13 clean/0 issues | VERDICT: APPROVE`
- **F3 — Real QA Execution**
  - `Scenarios [9/9 pass] | Integration [5/5] | Edge Cases [4 tested] | VERDICT: APPROVE`
- **F4 — Scope Fidelity Check**
  - `Tasks [13/13 compliant] | Contamination [CLEAN] | Unaccounted [CLEAN] | VERDICT: APPROVE`

## 6. Recommended usage flow

Use the workflow in this order:

1. `INIT` — create or rebuild the project workflow scaffold.
2. `REDEFINE` — re-state or re-sync project rules and planning semantics.
3. `UPDATE_TODO` — merge user-facing TODO updates against stable IDs from `plan.json`.
4. `START_WORK` — resume from `plan.json`, session state, and handoff context.
5. `FIX` — triage an issue and choose between `minimal_change` and `comprehensive_change` before implementation.

Operational rule: `docs/plan.json` is the execution source of truth. `PLAN.md` is the readable derived view, and `TODO.md` is the managed/local working view.

## 7. Migration notes

- Root `docs/*` are now framework-only and should not be reused as project runtime state.
- Project execution belongs under `projects/<PROJECT>/docs/*`.
- Markdown-first projects should backfill current execution state into `docs/plan.json` first, then regenerate or re-sync `PLAN.md` and managed `TODO.md` from that source.
- Managed TODO migration requires the `<!-- DEV_SDD:MANAGED:BEGIN --> ... <!-- DEV_SDD:MANAGED:END -->` block and stable `DEV_SDD:TASK:id=...` metadata derived from `plan.json`.
- `REDEFIND` is accepted only as a compatibility alias during migration; new usage should standardize on `REDEFINE`.

## 8. Remaining caveats / boundaries

- This workflow optimization governs framework docs, workflow commands, helper behavior, and workflow verification; it does not replace project-specific specs or domain logic.
- `START_WORK` may warn when TODO state drifts from managed `plan.json` state, but it remains plan-driven rather than TODO-driven.
- `FIX` is intentionally limited to triage and option generation; it does not itself apply code changes.
- The approval summary above reflects the verified repository state and recorded final-wave review results available at inspection time. If helpers or workflow docs change later, the workflow review/test gates should be rerun.
