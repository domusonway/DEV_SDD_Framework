# DEV_SDD Framework Gap Analysis and Improvement Plan

> Date: 2026-04-26  
> Scope: framework-level DEV_SDD capabilities  
> Goal: make DEV_SDD a personal-developer friendly AI agent framework that becomes smarter through long-term use.

---

## 1. Target Definition

DEV_SDD should evolve from a process-governance framework into a long-running personal AI development agent with these properties:

1. It remembers useful project, domain, and framework-level lessons.
2. It proactively resumes work, detects risks, and proposes next actions.
3. It balances autonomy with accuracy through explicit safety gates.
4. It supports both lightweight personal tasks and complex multi-module projects.
5. It prevents accumulated memory from becoming noisy context debt.

---

## 2. Current Baseline

The framework already has strong foundations:

1. Spec-driven development: `AGENTS.md`, `complexity-assess`, `tdd-cycle`, and `validate-output` define a SPEC -> tests -> implementation loop.
2. Layered memory: framework memory, domain memory, project memory, session snapshots, and candidates are separated.
3. Meta-Skill Loop: candidates can be created, reviewed, promoted, and synchronized with tests.
4. Session continuity: `start-work`, `session-snapshot`, and `HANDOFF.json` provide resume primitives.
5. Project execution truth: active project work is expected to flow through `projects/<PROJECT>/docs/plan.json`.

However, the current implementation still behaves more like a structured workflow than a mature self-improving agent.

---

## 3. Verified Problems

The following problems were observed during framework review:

1. Framework Layer 1 tests were not fully green: `skill-tests/run_all.py` reported 13/20 passing before this remediation work.
2. Runtime version assumptions were inconsistent: README requires Python 3.10+, while the active environment is Python 3.8.8.
3. Several tools and tests used Python 3.9/3.10 type syntax without postponed annotation evaluation.
4. `plan-tracker` failed under Python 3.8 before any plan command could run.
5. `start-work` could prioritize an old `status: in-progress` session even when `plan.json` was already 100% complete.
6. Hook behavior is partly documented but not always enforced by executable checks.
7. Candidate review has useful primitives but lacks enough lifecycle and quality-control actions for long-term use.
8. Parallel planning is represented in some project plans, but framework tools do not yet fully understand dependency graphs, parallel task pools, or write-conflict risks.

---

## 4. Problem A: Multi-Module Parallel Planning Is Underpowered

### Current Limitation

`plan.json` can contain fields such as `parallel_with`, `sync_points`, `relation_type`, and `associated_items`, but the framework tools mostly treat plans as ordered lists. This creates several issues:

1. The agent receives one `next_action` instead of a safe pool of runnable tasks.
2. Shared modules and fixtures are not protected by ownership or write-set checks.
3. There is no critical-path view to reduce waiting time.
4. There is no conflict forecast for tasks that may edit the same files or shared artifacts.
5. Merge gates and E2E slice ownership remain mostly manual.
6. `PLAN.md` is only a generated/readable view and should not become an execution source of truth.

### Required Direction

DEV_SDD should treat `plan.json` as a lightweight DAG:

1. `deps` / `blocked_by`: dependency edges.
2. `parallel_with` / `group`: safe concurrency hints.
3. `writes` / `reads` / `shared_artifacts`: conflict forecasting inputs.
4. `owner`: lane or role ownership.
5. `handoff_artifacts`: outputs that downstream tasks can consume.
6. `merge_gate`: required validation before the lane is considered integrated.

### Minimal Executable Remediation

1. `start-work` should expose a `parallel.ready_tasks` pool instead of only a single next action.
2. `start-work` should ignore stale in-progress sessions when the plan is complete.
3. `plan-tracker` should support:
   - `next --parallel`
   - `conflicts`
   - `critical-path`
4. `plan-tracker` should remain Python 3.8-compatible.

---

## 5. Problem B: Memory Sedimentation and Human Review Are Not Mature Enough

### Current Limitation

The framework already has `memory/candidates`, `skill-tracker`, `memory-update`, and Meta-Skill Loop agents. The gaps are lifecycle quality and long-term maintainability:

1. Candidate schema is only loosely enforced.
2. Review actions are too coarse: approve, reject, validate, promote.
3. There is no first-class defer/archive/project-only/merge action.
4. Direct append promotion can pollute target files over time.
5. Candidate effectiveness is not tracked after activation or promotion.
6. There is no rollback/deprecation path when a memory later proves wrong.
7. Memory loading is mostly keyword-based and can become noisy as memory grows.

### Required Direction

Memory should be treated as a managed knowledge system:

1. Candidates need evidence, scope, risk, status, and lifecycle metadata.
2. Human review should support more than approve/reject.
3. Promotion should be structured and reversible.
4. Memory use should be measurable: loaded, applied, helped, misled, or stale.
5. Old and low-value memory should be pruned or archived.

### Minimal Executable Remediation

1. `skill-tracker` should validate candidate schema.
2. `skill-tracker` should support `defer`, `archive`, and `project-only` actions.
3. Candidate status output should surface these lifecycle states.
4. Review metadata should be written back into candidate files for auditability.

---

## 6. Performance and Context Risks

1. Startup context can grow quickly because framework rules, project memory, sessions, plans, and candidates are all useful.
2. Context quality will degrade if memory is loaded by breadth rather than relevance.
3. More hooks and tools increase the chance of path, permission, or runtime-version failures.
4. Personal development workflows need a lower-friction path than enterprise-grade H-mode ceremony.

Required future work:

1. Top-k semantic memory retrieval.
2. Memory usage scoring and decay.
3. Lightweight mode for personal tasks.
4. Tool health checks that fail loudly for framework-critical tools.

---

## 7. Personal Developer Experience Requirements

DEV_SDD should offer three autonomy levels:

1. `safe_auto`: agent can proceed without asking for low-risk code/test/doc changes.
2. `ask_before_change`: agent asks before changing scope, specs, persistence, permissions, or shared contracts.
3. `manual_only`: agent only reports recommendations for destructive, irreversible, or broad framework changes.

It should also support three process weights:

1. `L`: lightweight BRIEF + focused tests + minimal memory decision.
2. `M`: SPEC + module tests + plan tracking.
3. `H`: DAG planning + lane handoff + E2E merge gates + memory review.

---

## 8. Priority Roadmap

### P0

1. Make framework Layer 1 tests pass in the active supported environment.
2. Resolve Python version compatibility or fail fast with a clear version check.
3. Prevent stale sessions from overriding completed plans.

### P1

1. Add parallel ready-task discovery to `start-work` and `plan-tracker`.
2. Add conflict forecast and critical-path reporting.
3. Extend candidate review lifecycle and schema validation.
4. Add prompt-policy injection so broad task classes receive explicit quality constraints.
5. Add memory usage/effectiveness tracking with prune and deprecate recommendations.
6. Add plan lock/release primitives to reduce parallel-lane overwrite risk.

### P2

1. Add memory effectiveness tracking.
2. Add pruning and aging workflows.
3. Add semantic memory retrieval.
4. Add personal lightweight mode defaults.

---

## 9. Acceptance Criteria for This Remediation Batch

1. `python3 skill-tests/run_all.py` passes Layer 1.
2. `python3 .claude/tools/plan-tracker/tracker.py status --json` runs under Python 3.8.
3. `python3 .claude/tools/plan-tracker/tracker.py next --parallel --json` returns a machine-readable task pool.
4. `python3 .claude/tools/plan-tracker/tracker.py conflicts --json` returns conflict analysis.
5. `python3 .claude/tools/plan-tracker/tracker.py critical-path --json` returns dependency depth analysis.
6. `python3 .claude/tools/start-work/run.py --json` includes `parallel` data and does not let stale sessions override a completed plan.
7. `python3 .claude/tools/skill-tracker/tracker.py validate-schema` reports candidate schema health.
8. `skill-tracker` supports `defer`, `archive`, and `project-only` lifecycle actions.
9. `.claude/skills/prompt-policy/SKILL.md` injects explicit quality constraints for review/evaluation/analysis, document creation, parallel planning, memory review, and implementation/fix tasks.
10. `.claude/tools/prompt-policy/run.py` can classify task text and emit `{matched,injected}`.
11. `.claude/tools/memory-usage/run.py` can record, summarize, prune, and deprecate memory usage signals.
12. `plan-tracker lock/release` can protect a module from accidental parallel overwrite.
13. `.claude/tools/context-probe/run.py` can classify task text, emit `{matched_dimensions,auto_load}`, and optionally record loaded memory entries to `memory_usage.jsonl`.
14. `start-work --task "..."` includes both `context_probe` and `prompt_policy` structured outputs.
15. `.claude/tools/framework-health/run.py --json` aggregates start-work, candidate schema/review, parallel planning, and memory pruning signals into one health report.
16. `.claude/tools/memory-search/run.py` ranks framework/project memory files for a task query and can record selected hits as loaded memory usage events.
