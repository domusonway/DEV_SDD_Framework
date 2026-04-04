# DEV SDD Framework · Framework Context

---

## Purpose

This document defines the **framework-level context** for DEV SDD itself.
It exists to explain what the framework governs, how work should be organized, and where execution state belongs.

It is **not** an active-project runtime document.

---

## Scope Boundary

### Root `docs/*` = framework docs

The root `docs/*` directory describes the shared framework model, command workflow, ownership rules, and guardrails that apply across projects.

Examples:
- `docs/CONTEXT.md` → framework purpose, boundaries, and operating model
- `docs/PLAN.md` → framework planning model and planning ownership rules
- `docs/TODO.md` → framework backlog model and framework maintenance work

### `projects/<PROJECT>/docs/*` = active-project execution docs

When a concrete project is active, its execution-facing documents live under `projects/<PROJECT>/docs/*`.
That is where project-specific context, generated plan views, TODO tracking, specs, and delivery notes belong.

The startup protocol in `AGENTS.md` remains authoritative for loading context:
- first load framework memory and framework rules
- then load the active project's `CLAUDE.md`, project memory, and latest session state
- then continue with project execution using project-scoped docs

---

## Execution Source of Truth

DEV SDD uses `plan.json` as the **execution source of truth** for active project work.

Implications:
- execution state must not drift back to markdown-first ownership
- markdown plan or todo documents may summarize or present execution state, but they do not override `plan.json`
- later commands and tools should reconcile against `plan.json` before claiming status, selecting next work, or updating project-facing task views

Root framework docs define these rules; project workflows execute them.

---

## Framework Architecture

```text
DEV SDD Framework
├── AGENTS.md                     # startup protocol and mandatory operating rules
├── docs/*                        # framework-only reference and workflow docs
├── memory/*                      # cross-project framework memory and candidates
├── .claude/skills/*              # reusable execution skills
├── .claude/hooks/*               # automatic safeguards and verification hooks
├── .claude/agents/*              # H-mode agent coordination roles
└── projects/<PROJECT>/...        # isolated project execution space
    ├── CLAUDE.md
    ├── docs/*
    ├── memory/*
    └── modules/*
```

---

## Operating Model

1. Framework rules are loaded first.
2. Active-project context is loaded second.
3. Specs drive tests, and tests drive implementation.
4. Hooks and validation prevent silent drift.
5. Memory and candidates capture reusable lessons back into the framework.

This keeps framework governance stable while allowing each project to own its own execution details.

---

## Relationship to Commands and Tools

This context document is the framework-side reference for command and tool behavior.

It should stay aligned with:
- `AGENTS.md` startup protocol language
- project ownership under `projects/<PROJECT>/docs/*`
- command/tool behavior that reads, reconciles, or generates project execution state from `plan.json`

If a command updates project execution status, it should do so in the project space and according to `plan.json` ownership, not by repurposing root framework docs as project templates.

---

## Shared Command/Backend Contract

The logical workflow commands `INIT`, `REDEFINE`, `UPDATE_TODO`, `START_WORK`, and `FIX` share one framework contract even when their user-facing entrypoints differ.

### Shared output envelope

All helper-backed command responses should use the reusable envelope `{status,message,data}`.

- `status`: `ok`, `warning`, or `error`
- `message`: a short human-readable summary of the result or degradation
- `data`: the structured payload consumed by agents or follow-up tools

This matches the existing helper/tool pattern already visible in:
- `.claude/tools/start-work/run.py`
- `.claude/tools/sdd-cli/cli.py`
- `.claude/tools/plan-tracker/tracker.py`

### Ownership and source of truth

- `START_WORK` is primarily read-oriented. It reports context/session/plan state and follows plan precedence `plan.json` → `PLAN.md` → `IMPLEMENTATION_PLAN.md`.
- `UPDATE_TODO` may refresh human-readable task views or project-local TODO records, but it must reconcile against `projects/<PROJECT>/docs/plan.json` before claiming execution state.
- `INIT`, `REDEFINE`, and `FIX` must preserve the same ownership boundary: root `docs/*` define framework rules, while project execution artifacts live under `projects/<PROJECT>/docs/*`.
- No command may treat root `docs/PLAN.md` or root `docs/TODO.md` as the active-project execution source of truth.

### Confirmation policy

- `START_WORK` does not require confirmation for read-only inspection.
- `INIT` requires confirmation before creating or replacing user-visible project scaffolding when intent, target project, or affected files are not already explicit.
- `REDEFINE` requires confirmation before changing user-facing scope, specs, or planning semantics.
- `UPDATE_TODO` requires confirmation when it would rewrite user-facing task wording, resolve ambiguity, or change task state beyond a straightforward user-requested sync.
- `FIX` may proceed without extra confirmation for a clearly requested implementation correction, but must ask first if the fix would redefine scope, change specs/plans, or discard user-authored execution notes.

### Graceful degradation rules

- Missing active project: return `warning`, explain what is missing, and provide a `next_action` in `data`.
- Missing project directory or project docs: return `warning` unless the command cannot continue safely.
- Missing session or handoff data: degrade to a new-session/default path instead of failing.
- Missing structured plan data: fall back to `PLAN.md`, then `IMPLEMENTATION_PLAN.md`, and report which source was used.
- Malformed or contradictory source data: return `error` only when safe continuation is impossible; otherwise return `warning` plus the degraded path.

### Slash-command docs vs. helper CLI behavior

- Slash-command docs define the user-facing contract: intent, required confirmation points, ownership rules, and what the command is allowed to mutate.
- Helper CLIs define the executable backend behavior: probing files, reconciling structured state, rendering outputs, and emitting the `{status,message,data}` envelope.
- `START_WORK` already has a concrete helper in `.claude/tools/start-work/run.py`; its slash-command doc must describe the workflow without promising hidden side effects beyond what the helper actually reports.
- Until dedicated helpers exist, `INIT`, `REDEFINE`, `UPDATE_TODO`, and `FIX` remain bound by this shared contract language but should not claim backend behavior that is not yet implemented.

---

## Constraints

- Do not treat root `docs/CONTEXT.md` as a project template.
- Do not place active-project execution state in root `docs/*`.
- Do not let generated markdown summaries supersede `plan.json`.
- Keep terminology compatible with the startup protocol and memory-loading model in `AGENTS.md`.
