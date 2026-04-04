# DEV SDD Framework · Framework TODO

---

## Purpose

This document is the **framework-level TODO and backlog guide** for DEV SDD itself.
It tracks framework maintenance, documentation debt, workflow improvements, and follow-up work that affects the shared framework.

It is **not** the active runtime queue for any concrete project.

---

## Scope Boundary

### Root `docs/TODO.md` = framework backlog

Use this file for framework-facing work such as:
- framework documentation cleanup
- command / hook / agent workflow improvements
- skill-test coverage gaps for the framework
- template and generator quality issues
- cross-project maintenance follow-ups

This file should describe backlog items and execution guidance for the framework, not day-to-day delivery state for an active project.

### `projects/<PROJECT>/docs/TODO.md` = project TODO

Use `projects/<PROJECT>/docs/TODO.md` for project-scoped execution notes when a specific project needs a human-readable TODO view.

Project TODOs may contain runtime-oriented records such as:
- current delivery follow-ups
- temporary execution notes
- structured `[STUCK]` records required by hooks or recovery flows
- skip reasons or other project-local audit notes

Those project TODO records belong in the project space, not in the root framework TODO.

---

## Relationship to Other Sources of Truth

- Root `docs/TODO.md` does **not** own active-project execution state.
- For active project work, `projects/<PROJECT>/docs/plan.json` remains the execution source of truth.
- A project TODO may summarize local work or hold structured records, but it does not override project execution data.
- Root docs define governance and backlog semantics; projects own execution details.

---

## Framework TODO Usage Rules

When updating this file:

1. Keep entries framework-scoped.
2. Do not place active-project task queues here.
3. Do not copy template placeholders into this file.
4. Do not leave HTML residue or generator noise.
5. If a workflow requires `[STUCK]` logging, record it in the relevant project TODO, not here.

---

## Framework Backlog

- Review framework command and agent ownership boundaries for consistency with root docs.
- Improve framework-generated project artifacts so root/project document semantics do not drift.
- Expand framework skill-tests for TODO/STUCK ownership expectations where needed.
- Track framework maintenance work that affects reusable hooks, skills, templates, or validation tooling.

---

## Notes

- Root TODO = framework backlog and framework execution guidance.
- Project TODO = `projects/<PROJECT>/docs/TODO.md` for project-local execution notes.
- Structured project records such as `[STUCK]` notes remain valid in project TODOs when required by hooks.
