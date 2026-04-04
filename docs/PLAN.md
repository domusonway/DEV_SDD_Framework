# DEV SDD Framework · Planning Model

---

## Purpose

This document defines the **framework-level planning model** for DEV SDD.
It explains where planning authority lives, how project planning state is represented, and how markdown plan views must relate to structured execution data.

It is **not** a project template and it is **not** the live execution plan for any active project.

---

## Scope Boundary

### Root `docs/PLAN.md` = framework planning guidance

The root `docs/PLAN.md` describes shared planning rules for the framework itself:
- what file is authoritative for active-project execution state
- how generated plan views should be interpreted
- how commands and agents should avoid status drift
- how planning ownership relates to other framework docs

It does not hold project batches, module checklists, milestone dates, or active delivery progress.

### `projects/<PROJECT>/docs/*` = project execution planning

Active-project planning artifacts live under `projects/<PROJECT>/docs/*`.
That is where a concrete project's structured plan, generated plan view, and any legacy plan markdown belong.

At the project level:
- `projects/<PROJECT>/docs/plan.json` holds the execution state
- `projects/<PROJECT>/docs/PLAN.md` is a derived or generated markdown view
- `projects/<PROJECT>/docs/IMPLEMENTATION_PLAN.md` is a fallback legacy markdown source when structured plan data does not yet exist

---

## Planning Source of Truth

For active project work, `plan.json` is the **source of truth** and the authoritative execution plan.

That means:
- agents must read `projects/<PROJECT>/docs/plan.json` before claiming project progress when it exists
- task state transitions must be written against `plan.json`, not inferred from markdown alone
- generated markdown may summarize status for humans, but it must not override structured state
- framework documentation must preserve this ownership model and must not reintroduce markdown-first planning

This rule keeps execution planning machine-readable, tool-safe, and resistant to manual drift.

---

## `plan.json` Responsibilities

The framework expects project `plan.json` files to carry the execution state needed by tools and agents, including:
- batch ordering
- module membership per batch
- dependency links
- module state such as `pending`, `in_progress`, `completed`, or `skipped`
- milestone metadata when applicable

The template at `projects/_template/docs/plan.json` shows the expected shape.
Framework guidance may evolve, but project execution authority remains with `plan.json`.

---

## Generated `PLAN.md` Semantics

Project `PLAN.md` is a **derived view**, not the execution authority.

Its purpose is to provide a readable snapshot of project planning status for humans, for example:
- batch/module checklist rendering
- progress summaries
- dependency reminders
- timestamps from the latest render

Because it is derived:
- it may be regenerated from `plan.json`
- manual edits are not authoritative and may be overwritten
- agents should treat discrepancies in favor of `plan.json`

When a project still relies on markdown planning, the framework may read `PLAN.md` or `IMPLEMENTATION_PLAN.md` as compatibility fallbacks, but those are lower-precedence sources.

---

## Command and Tool Alignment

Framework wording must stay aligned with actual tool behavior.

Current planning precedence is:
1. `plan.json`
2. `PLAN.md`
3. `IMPLEMENTATION_PLAN.md`

This matches `start-work/run.py`, which checks project planning state in that order.
It also matches `plan-tracker/tracker.py`, which treats `projects/<PROJECT>/docs/plan.json` as the writable execution record and renders project `PLAN.md` as a read-only output.

If future tools report project status, choose next work, or reconcile progress, they should follow the same precedence unless the framework rules are intentionally revised everywhere together.

---

## Anti-Drift Rules

To prevent planning drift across framework docs, project docs, and tools:

1. Do not use root `docs/PLAN.md` as a project plan template.
2. Do not store active-project execution checklists in root `docs/PLAN.md`.
3. Do not treat project `PLAN.md` as authoritative when `plan.json` exists.
4. Do not let generated markdown silently diverge from `plan.json` semantics.
5. When updating framework docs, keep ownership language consistent with `docs/CONTEXT.md`.
6. When updating commands or agents, preserve or explicitly migrate the precedence chain `plan.json` -> `PLAN.md` -> `IMPLEMENTATION_PLAN.md`.

Any framework change that weakens these rules risks reintroducing planning ambiguity and execution-state drift.

---

## Relationship to Other Root Docs

- `docs/CONTEXT.md` defines the framework-level ownership boundary for root vs. project docs.
- `docs/PLAN.md` defines the planning authority model within that boundary.
- `docs/TODO.md` remains a framework maintenance backlog document and should not be repurposed as active project execution state.

Together, these root docs describe the framework's governance model; project execution remains under `projects/<PROJECT>/docs/*`.
