# DEV_SDD Framework Documentation and Command Realignment

## TL;DR

> **Quick Summary**: Realign DEV_SDD around a single execution source of truth (`plan.json`), normalize framework-level root docs, and add a coherent command/tool workflow for `INIT`, `REDEFINE`, `UPDATE_TODO`, `START_WORK`, and `FIX`.
>
> **Deliverables**:
> - Framework-level `docs/CONTEXT.md`, `docs/PLAN.md`, and `docs/TODO.md` redefined and normalized
> - Command specs for `DEV_SDD:INIT`, `DEV_SDD:REDEFINE`, `DEV_SDD:UPDATE_TODO`, `DEV_SDD:START_WORK`, and `DEV_SDD:FIX`
> - CLI/backend support aligned to slash-command docs
> - `plan.json`-centric TODO reconciliation and merge rules
> - TDD coverage and regression guardrails for workflow drift
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: 1 -> 4 -> 6/7/8/9/10 -> 11 -> 12 -> 13

---

## Context

### Original Request
Optimize the DEV_SDD agent around five command capabilities: `DEV_SDD:INIT`, `DEV_SDD:REDEFINE`, `DEV_SDD:UPDATE_TODO`, `DEV_SDD:START_WORK`, and `DEV_SDD:FIX`. First, straighten out the framework-level root docs `docs/CONTEXT.md`, `docs/PLAN.md`, and `docs/TODO.md`, then repair and improve the framework sequentially.

### Interview Summary
**Key Discussions**:
- Root `docs/*` are framework-level documents only, not active-project execution docs.
- Canonical command name is `DEV_SDD:REDEFINE`.
- `plan.json` remains the execution source of truth; markdown drift must be corrected.
- `DEV_SDD:START_WORK` must read project memory/session state and reconcile unfinished `projects/<PROJECT>/docs/TODO.md` items against `plan.json`.
- `DEV_SDD:UPDATE_TODO` must support partial/local updates, preserve user edits, and confirm affected items interactively.
- Delivery model is slash-command docs plus explicit CLI/backend support.
- Test strategy is TDD first.

**Research Findings**:
- Root `docs/CONTEXT.md` and `docs/PLAN.md` are still template placeholders; root `docs/TODO.md` is a mixed backlog with template residue and stale/conflicting items.
- Existing `/DEV_SDD:start-work` already implements plan precedence (`plan.json` -> `PLAN.md` -> `IMPLEMENTATION_PLAN.md`) plus session/handoff handling.
- `plan-tracker` already treats `projects/<PROJECT>/docs/plan.json` as authoritative and `PLAN.md` as generated.
- Existing command architecture uses `.claude/commands/*.md` plus Python helpers with `{status,message,data}` outputs.
- External workflow references support explicit handoff/session state and structured bug triage before action selection.

### Metis Review
**Identified Gaps** (addressed):
- Metis consultation was attempted multiple times but timed out; equivalent gap coverage was synthesized from the command audit, root-doc audit, Oracle guidance, and explicit user confirmations.
- Guardrails added for source-of-truth ownership, partial TODO merge behavior, and TODO-vs-plan reconciliation.
- Migration work explicitly includes anti-drift checks for old markdown-first behavior.

---

## Work Objectives

### Core Objective
Make DEV_SDD internally consistent by separating framework docs from project execution docs, enforcing `plan.json` as execution truth, and designing a tested command/tool workflow that safely initializes, redefines, updates TODO state, resumes work, and fixes issues.

### Concrete Deliverables
- Rewritten framework-level `docs/CONTEXT.md`
- Rewritten framework-level `docs/PLAN.md`
- Rewritten framework-level `docs/TODO.md`
- Updated project template and command docs aligned to `plan.json`
- New or extended helper tooling for `INIT`, `REDEFINE`, `UPDATE_TODO`, and `FIX`
- Enhanced `START_WORK` reconciliation behavior
- Automated tests covering command behavior and drift prevention

### Definition of Done
- [ ] Root framework docs are no longer template placeholders and clearly define framework-level responsibilities.
- [ ] `plan.json` ownership is documented and enforced across commands/tooling.
- [ ] `UPDATE_TODO` supports partial updates with stable IDs and confirmation.
- [ ] `START_WORK` reconciles TODO items against `plan.json` and session state.
- [ ] `FIX` presents minimal-change and comprehensive-change options before implementation.
- [ ] Automated tests cover new workflow behavior and historical drift cases.

### Must Have
- Keep `plan.json` as the authoritative execution-state source.
- Preserve user-authored TODO content through merge/confirmation rules.
- Keep root docs framework-scoped and project docs project-scoped.
- Reuse existing command/tool patterns instead of creating a parallel workflow.

### Must NOT Have (Guardrails)
- No return to markdown-first execution state ownership.
- No silent overwrites of existing project docs or TODO user edits.
- No duplication of logic between slash-command docs and helper CLIs.
- No ambiguous ownership between root framework docs and `projects/<PROJECT>/docs/*`.

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: TDD
- **Framework**: Python-based repo tests plus `skill-tests`
- **If TDD**: Each implementation task follows RED -> GREEN -> REFACTOR

### QA Policy
Every task must include agent-executed QA scenarios and evidence saved under `.sisyphus/evidence/`.

- **Docs/Markdown validation**: Bash (`python3`, `grep`, repo test commands)
- **CLI behavior**: Bash (`python3 ... --json`) with output assertions
- **Workflow state checks**: Bash reading generated files and comparing expected fields
- **Regression coverage**: repo test commands and targeted scenario scripts

---

## Execution Strategy

### Parallel Execution Waves

```text
Wave 1 (Start Immediately — source-of-truth and document foundations):
├── Task 1: Redefine framework CONTEXT.md [writing]
├── Task 2: Redefine framework PLAN.md around plan.json [writing]
├── Task 3: Redefine framework TODO.md model [writing]
├── Task 4: Define shared command/backend contract [deep]
└── Task 5: Align project template ownership rules [unspecified-high]

Wave 2 (After Wave 1 — command-specific design and TDD):
├── Task 6: INIT command + overwrite-confirmation flow [unspecified-high]
├── Task 7: REDEFINE propagation and resync flow [deep]
├── Task 8: UPDATE_TODO stable-ID merge flow [deep]
├── Task 9: START_WORK TODO reconciliation flow [deep]
└── Task 10: FIX triage + optioning flow [unspecified-high]

Wave 3 (After Wave 2 — integration, drift prevention, rollout):
├── Task 11: Unify CLI wiring and JSON output contracts [unspecified-high]
├── Task 12: Add regression/lint guardrails against drift [deep]
└── Task 13: Migration and rollout documentation [writing]

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real QA execution (unspecified-high)
└── Task F4: Scope fidelity check (deep)
```

### Dependency Matrix

- **1**: — -> 6, 7, 13
- **2**: — -> 6, 7, 8, 9, 11, 13
- **3**: — -> 8, 9, 13
- **4**: — -> 6, 7, 8, 9, 10, 11
- **5**: — -> 6, 7, 8, 9, 10, 13
- **6**: 1, 2, 4, 5 -> 11, 12
- **7**: 1, 2, 4, 5 -> 11, 12, 13
- **8**: 2, 3, 4, 5 -> 11, 12, 13
- **9**: 2, 3, 4, 5 -> 11, 12, 13
- **10**: 4, 5 -> 11, 12, 13
- **11**: 6, 7, 8, 9, 10 -> 12, 13, FINAL
- **12**: 6, 7, 8, 9, 10, 11 -> FINAL
- **13**: 1, 2, 3, 5, 7, 8, 9, 10, 11 -> FINAL

### Agent Dispatch Summary

- **Wave 1**: 5 tasks — T1/T2/T3 -> `writing`, T4 -> `deep`, T5 -> `unspecified-high`
- **Wave 2**: 5 tasks — T6 -> `unspecified-high`, T7/T8/T9 -> `deep`, T10 -> `unspecified-high`
- **Wave 3**: 3 tasks — T11 -> `unspecified-high`, T12 -> `deep`, T13 -> `writing`
- **FINAL**: 4 tasks — F1 -> `oracle`, F2 -> `unspecified-high`, F3 -> `unspecified-high`, F4 -> `deep`

---

## TODOs

---

- [x] 1. Redefine framework `docs/CONTEXT.md`

  **What to do**:
  - Replace placeholder/template framing with framework-level purpose, scope, architecture, and boundaries.
  - Explicitly state that root `docs/*` govern the framework, while active-project execution docs live under `projects/<PROJECT>/docs/*`.
  - Add TDD-facing references to how framework docs relate to command/tool behavior.

  **Must NOT do**:
  - Do not leave `{{...}}` placeholders.
  - Do not describe root docs as active-project runtime documents.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: This is a framework-document redesign task with terminology and structure sensitivity.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `playwright`: no UI behavior involved.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with 2, 3, 4, 5)
  - **Blocks**: 6, 7, 13
  - **Blocked By**: None

  **References**:
  - `docs/CONTEXT.md` - Current broken placeholder source to replace.
  - `docs/PLAN.md` - Must remain consistent with the new framework-level context vocabulary.
  - `docs/TODO.md` - Must align with the ownership split documented here.
  - `projects/_template/CLAUDE.md:36-44` - Existing project-level load-map pattern that root docs must not duplicate.
  - `AGENTS.md:8-29` - Startup protocol context that framework docs should support, not contradict.

  **Acceptance Criteria**:
  - [ ] `docs/CONTEXT.md` contains no template placeholders.
  - [ ] It explicitly distinguishes framework docs from project docs.
  - [ ] It references `plan.json`-centric execution ownership consistently.

  **QA Scenarios**:
  ```text
  Scenario: Framework context doc is instantiated and scoped correctly
    Tool: Bash
    Preconditions: Changes to docs are applied
    Steps:
      1. Run `python3 - <<'PY'
from pathlib import Path
text = Path('docs/CONTEXT.md').read_text()
assert '{{' not in text and '}}' not in text
assert 'framework' in text.lower()
assert 'projects/<PROJECT>/docs' in text or 'projects/<project>' in text.lower()
PY`
      2. Save terminal output
    Expected Result: Command exits 0 with no assertion failures
    Failure Indicators: Placeholder remains, missing scope split, non-zero exit
    Evidence: .sisyphus/evidence/task-1-framework-context-scope.txt

  Scenario: Root/project ownership wording does not conflict with template docs
    Tool: Bash
    Preconditions: Changes to docs are applied
    Steps:
      1. Run `python3 - <<'PY'
from pathlib import Path
root = Path('docs/CONTEXT.md').read_text()
tmpl = Path('projects/_template/CLAUDE.md').read_text()
assert 'framework-level' in root.lower() or 'framework level' in root.lower()
assert '当前进度' in tmpl
PY`
      2. Save terminal output
    Expected Result: Command exits 0 and confirms intentional ownership separation
    Failure Indicators: Root doc still reads like project template; non-zero exit
    Evidence: .sisyphus/evidence/task-1-framework-context-ownership.txt
  ```

  **Commit**: YES
  - Message: `docs(framework): redefine root context ownership`
  - Files: `docs/CONTEXT.md`
  - Pre-commit: `python3 - <<'PY' ... PY`

- [x] 2. Redefine framework `docs/PLAN.md` around `plan.json`

  **What to do**:
  - Rewrite root `docs/PLAN.md` to describe framework execution planning, `plan.json` authority, generated-plan expectations, and anti-drift rules.
  - Remove template batch placeholders.
  - Document the relationship among root framework plan guidance, project `plan.json`, and generated project `PLAN.md` views.

  **Must NOT do**:
  - Do not let markdown plan text re-become execution truth.
  - Do not conflict with existing `plan-tracker` behavior.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: This is documentation architecture with normative rules.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `git-master`: no VCS-specific reasoning required.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with 1, 3, 4, 5)
  - **Blocks**: 6, 7, 8, 9, 11, 13
  - **Blocked By**: None

  **References**:
  - `docs/PLAN.md` - Current placeholder document to normalize.
  - `projects/_template/docs/plan.json` - Canonical execution-state structure to preserve.
  - `.claude/tools/plan-tracker/tracker.py:3-11` - States that `plan.json` is source of truth and `PLAN.md` is generated.
  - `.claude/tools/start-work/run.py:207-228` - Existing plan detection precedence.
  - `.claude/commands/dev-sdd-start-work.md:34-40` - Command doc already advertises the same precedence.

  **Acceptance Criteria**:
  - [ ] Root `docs/PLAN.md` no longer contains template placeholders.
  - [ ] It explicitly names `plan.json` as execution truth.
  - [ ] It explains generated-vs-manual ownership without ambiguity.

  **QA Scenarios**:
  ```text
  Scenario: Root PLAN doc enforces plan.json ownership
    Tool: Bash
    Preconditions: Changes to docs are applied
    Steps:
      1. Run `python3 - <<'PY'
from pathlib import Path
text = Path('docs/PLAN.md').read_text()
assert '{{' not in text and '}}' not in text
assert 'plan.json' in text
assert 'source of truth' in text.lower() or 'authoritative' in text.lower()
PY`
      2. Save terminal output
    Expected Result: Command exits 0
    Failure Indicators: Missing plan.json ownership wording; non-zero exit
    Evidence: .sisyphus/evidence/task-2-root-plan-ownership.txt

  Scenario: Root PLAN wording matches tool precedence
    Tool: Bash
    Preconditions: Changes to docs are applied
    Steps:
      1. Run `python3 - <<'PY'
from pathlib import Path
doc = Path('docs/PLAN.md').read_text()
tool = Path('.claude/tools/start-work/run.py').read_text()
assert 'plan.json' in doc and 'PLAN.md' in doc
assert 'plan.json' in tool and 'IMPLEMENTATION_PLAN.md' in tool
PY`
      2. Save terminal output
    Expected Result: Command exits 0 and confirms matching precedence vocabulary
    Failure Indicators: Plan doc contradicts helper precedence; non-zero exit
    Evidence: .sisyphus/evidence/task-2-root-plan-precedence.txt
  ```

  **Commit**: YES
  - Message: `docs(framework): redefine plan ownership model`
  - Files: `docs/PLAN.md`
  - Pre-commit: `python3 - <<'PY' ... PY`

- [x] 3. Redefine framework `docs/TODO.md` model

  **What to do**:
  - Convert root `docs/TODO.md` into a framework-level backlog/execution-guidance document consistent with the new framework scope.
  - Remove template residue, stale framing, and HTML noise.
  - Clarify how framework TODO governance differs from project `docs/TODO.md` execution queues.

  **Must NOT do**:
  - Do not let root TODO masquerade as active project task state.
  - Do not silently discard meaningful legacy backlog items; reframe them intentionally.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Requires editorial cleanup plus workflow framing.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: no UI work.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with 1, 2, 4, 5)
  - **Blocks**: 8, 9, 13
  - **Blocked By**: None

  **References**:
  - `docs/TODO.md` - Current mixed backlog requiring normalization.
  - `skill-tests/generated/cases.json:501-505` - Existing expectation that TODO can hold structured state like STUCK records.
  - `README.md:145-163` - Current startup framing that TODO should not contradict.
  - `projects/_template/CLAUDE.md:40-41` - Project template points to project TODO as current progress.

  **Acceptance Criteria**:
  - [ ] Root TODO no longer includes template placeholders or HTML residue.
  - [ ] It clearly distinguishes framework backlog from project execution TODOs.
  - [ ] Any preserved legacy tasks are categorized intentionally.

  **QA Scenarios**:
  ```text
  Scenario: Root TODO is normalized and placeholder-free
    Tool: Bash
    Preconditions: Changes to docs are applied
    Steps:
      1. Run `python3 - <<'PY'
from pathlib import Path
text = Path('docs/TODO.md').read_text()
assert '{{' not in text and '}}' not in text
assert '<br />' not in text and '&#x20;' not in text
PY`
      2. Save terminal output
    Expected Result: Command exits 0
    Failure Indicators: Placeholder or HTML noise remains
    Evidence: .sisyphus/evidence/task-3-root-todo-normalized.txt

  Scenario: Root TODO does not claim active project execution ownership
    Tool: Bash
    Preconditions: Changes to docs are applied
    Steps:
      1. Run `python3 - <<'PY'
from pathlib import Path
text = Path('docs/TODO.md').read_text().lower()
assert 'framework' in text
assert 'project todo' in text or 'projects/<project>/docs/todo.md' in text
PY`
      2. Save terminal output
    Expected Result: Command exits 0
    Failure Indicators: TODO still reads like project runtime queue without distinction
    Evidence: .sisyphus/evidence/task-3-root-todo-scope.txt
  ```

  **Commit**: YES
  - Message: `docs(framework): normalize root todo model`
  - Files: `docs/TODO.md`
  - Pre-commit: `python3 - <<'PY' ... PY`

- [x] 4. Define shared command/backend contract

  **What to do**:
  - Define common input/output schema, confirmation policy, source-of-truth ownership, and error/degradation rules for `INIT`, `REDEFINE`, `UPDATE_TODO`, `START_WORK`, and `FIX`.
  - Standardize `{status,message,data}` output expectations and conflict-handling language.
  - Define where slash-command docs end and helper CLIs begin.

  **Must NOT do**:
  - Do not let each command invent its own contract shape.
  - Do not duplicate business logic in both markdown and Python entrypoints.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Cross-command workflow architecture and consistency constraints.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `writing`: architecture consistency is primary; prose is secondary.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with 1, 2, 3, 5)
  - **Blocks**: 6, 7, 8, 9, 10, 11
  - **Blocked By**: None

  **References**:
  - `.claude/commands/dev-sdd-start-work.md` - Existing slash-command contract pattern.
  - `.claude/tools/start-work/run.py:35-50` - Existing output contract example.
  - `.claude/tools/sdd-cli/cli.py:71-85` - Shared structured output behavior.
  - `.claude/tools/plan-tracker/tracker.py:112-160` - JSON status output for plan state.

  **Acceptance Criteria**:
  - [ ] Shared contract rules exist for all five commands.
  - [ ] Output schema and confirmation semantics are explicit.
  - [ ] Source-of-truth ownership is documented for every command.

  **QA Scenarios**:
  ```text
  Scenario: Command contract spec covers all five commands and shared schema
    Tool: Bash
    Preconditions: Contract doc/spec changes are applied
    Steps:
      1. Run `python3 - <<'PY'
from pathlib import Path
targets = ['INIT','REDEFINE','UPDATE_TODO','START_WORK','FIX']
text = '\n'.join(Path(p).read_text() for p in ['docs/CONTEXT.md','docs/PLAN.md','docs/TODO.md','.claude/commands/dev-sdd-start-work.md'] if Path(p).exists())
for t in targets:
    assert t in text
assert '{status,message,data}' in text or 'status,message,data' in text
PY`
      2. Save terminal output
    Expected Result: Command exits 0
    Failure Indicators: Missing command contract coverage or schema wording
    Evidence: .sisyphus/evidence/task-4-command-contract-coverage.txt

  Scenario: Existing helper outputs remain aligned with documented contract
    Tool: Bash
    Preconditions: Contract updates are applied
    Steps:
      1. Run `python3 .claude/tools/start-work/run.py --json > .sisyphus/evidence/task-4-start-work-sample.json || true`
      2. Run `python3 - <<'PY'
import json
from pathlib import Path
p = Path('.sisyphus/evidence/task-4-start-work-sample.json')
data = json.loads(p.read_text())
assert 'status' in data and 'message' in data and 'data' in data
PY`
    Expected Result: Sample helper output parses with expected top-level keys
    Failure Indicators: Missing schema fields or invalid JSON
    Evidence: .sisyphus/evidence/task-4-start-work-sample.json
  ```

  **Commit**: YES
  - Message: `docs(commands): define shared workflow contract`
  - Files: relevant `docs/*.md`, command docs
  - Pre-commit: `python3 .claude/tools/start-work/run.py --json`

- [x] 5. Align project template ownership rules

  **What to do**:
  - Update project template docs and entrypoints so they consistently point to project-level `plan.json`, generated `PLAN.md`, and project `TODO.md` roles.
  - Ensure template language does not reinforce historical markdown-first drift.
  - Preserve compatibility with current startup protocol references.

  **Must NOT do**:
  - Do not break current active-project detection or project load maps.
  - Do not redefine root framework docs inside project templates.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Cross-file contract alignment between template docs and helper tools.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `writing`: template/tool alignment matters more than prose alone.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with 1, 2, 3, 4)
  - **Blocks**: 6, 7, 8, 9, 10, 13
  - **Blocked By**: None

  **References**:
  - `projects/_template/CLAUDE.md` - Current project load-map contract.
  - `projects/_template/docs/plan.json` - Canonical project execution structure.
  - `.claude/commands/new-project.md` - Project creation flow that must stay compatible.
  - `README.md:145-163` - Public workflow documentation mentioning start-work and plan helpers.

  **Acceptance Criteria**:
  - [ ] Template docs clearly preserve project-scope ownership.
  - [ ] Template wording matches `plan.json`-centric behavior.
  - [ ] `/project:new` flow remains semantically compatible.

  **QA Scenarios**:
  ```text
  Scenario: Project template points to project-scoped execution artifacts
    Tool: Bash
    Preconditions: Template docs are updated
    Steps:
      1. Run `python3 - <<'PY'
from pathlib import Path
text = Path('projects/_template/CLAUDE.md').read_text()
assert 'docs/TODO.md' in text
assert 'memory/INDEX.md' in text
PY`
      2. Save terminal output
    Expected Result: Template keeps project-level load-map references
    Failure Indicators: Missing project-scope references
    Evidence: .sisyphus/evidence/task-5-template-loadmap.txt

  Scenario: Template and plan-tracker stay aligned on plan.json authority
    Tool: Bash
    Preconditions: Template/docs updates are applied
    Steps:
      1. Run `python3 - <<'PY'
from pathlib import Path
tmpl = Path('projects/_template/docs/plan.json').read_text()
tool = Path('.claude/tools/plan-tracker/tracker.py').read_text()
assert 'state' in tmpl and 'batches' in tmpl
assert 'plan.json' in tool and 'generated' in tool.lower()
PY`
      2. Save terminal output
    Expected Result: Command exits 0
    Failure Indicators: Template/tool contract drift
    Evidence: .sisyphus/evidence/task-5-template-planjson-contract.txt
  ```

  **Commit**: YES
  - Message: `docs(template): align project ownership rules`
  - Files: `projects/_template/**/*`, related docs
  - Pre-commit: `python3 - <<'PY' ... PY`

- [x] 6. Specify `DEV_SDD:INIT` bootstrap flow

  **What to do**:
  - Define the slash-command spec and helper/backend behavior for initializing project docs from `projects/<PROJECT>/docs/CONTEXT.md`.
  - Include generation of `plan.json`, generated/derived docs, overwrite detection, diff display, and interactive confirmation before replacing existing content.
  - Define how memory/history may be consulted safely during initialization.

  **Must NOT do**:
  - Do not overwrite existing project docs silently.
  - Do not initialize project docs from root framework docs by mistake.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Command behavior, confirmation UX, and file ownership all interact here.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `deep`: architecture prerequisites are already set by Task 4.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with 7, 8, 9, 10)
  - **Blocks**: 11, 12
  - **Blocked By**: 1, 2, 4, 5

  **References**:
  - `.claude/commands/new-project.md` - Existing project bootstrap pattern.
  - `projects/_template/CLAUDE.md` - Project doc outputs to align.
  - `projects/_template/docs/plan.json` - Must be generated or instantiated by the new flow.
  - `.claude/tools/start-work/run.py` - Existing project-resolution behavior to reuse.

  **Acceptance Criteria**:
  - [ ] INIT contract defines inputs, outputs, overwrite detection, and confirmation steps.
  - [ ] INIT explicitly creates or updates `plan.json` as execution truth.
  - [ ] Tests cover empty-doc bootstrap and existing-doc overwrite prompts.

  **QA Scenarios**:
  ```text
  Scenario: INIT bootstrap on empty fixture project produces expected artifact plan
    Tool: Bash
    Preconditions: Fixture `skill-tests/fixtures/init/empty-project/` exists with only `docs/CONTEXT.md`
    Steps:
      1. Run `python3 .claude/tools/init/run.py skill-tests/fixtures/init/empty-project --json --dry-run | tee .sisyphus/evidence/task-6-init-bootstrap.txt`
      2. Run `python3 -m pytest skill-tests/cases/test_init_tool.py -k bootstrap_empty_project -q | tee -a .sisyphus/evidence/task-6-init-bootstrap.txt`
      3. Assert the saved output contains `plan.json`, `PLAN.md`, `CLAUDE.md`, `AGENTS.md`, and `README.md`
    Expected Result: Helper exits 0 in dry-run mode and pytest reports `1 passed`
    Failure Indicators: Missing `plan.json`, wrong target paths, missing dry-run payload, or pytest failure
    Evidence: .sisyphus/evidence/task-6-init-bootstrap.txt

  Scenario: INIT detects existing docs and requires confirmation
    Tool: Bash
    Preconditions: Fixture `skill-tests/fixtures/init/existing-docs-project/` contains pre-existing generated targets
    Steps:
      1. Run `python3 .claude/tools/init/run.py skill-tests/fixtures/init/existing-docs-project --json --dry-run | tee .sisyphus/evidence/task-6-init-overwrite-guard.txt`
      2. Run `python3 -m pytest skill-tests/cases/test_init_tool.py -k existing_docs_require_confirmation -q | tee -a .sisyphus/evidence/task-6-init-overwrite-guard.txt`
      3. Assert output contains a confirmation-needed status or overwrite prompt metadata
    Expected Result: Existing content is not overwritten automatically and pytest reports `1 passed`
    Failure Indicators: Silent overwrite or missing prompt metadata
    Evidence: .sisyphus/evidence/task-6-init-overwrite-guard.txt
  ```

  **Commit**: YES
  - Message: `feat(init): define bootstrap and overwrite flow`
  - Files: new command doc, helper backend, tests
  - Pre-commit: targeted tests for INIT

- [x] 7. Specify `DEV_SDD:REDEFINE` propagation flow

  **What to do**:
  - Define how requirement changes update project planning while preserving `plan.json` authority.
  - Specify propagation order from revised planning inputs into derived docs and command-visible state.
  - Define alias/compatibility handling for legacy `REDEFIND` mentions if needed.

  **Must NOT do**:
  - Do not let REDEFINE reintroduce `PLAN.md` as the canonical state source.
  - Do not update downstream docs without recording what changed.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: This task governs resynchronization semantics and state ownership across documents.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `writing`: propagation semantics matter more than wording alone.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with 6, 8, 9, 10)
  - **Blocks**: 11, 12, 13
  - **Blocked By**: 1, 2, 4, 5

  **References**:
  - `docs/PLAN.md` - Framework-level plan ownership rules.
  - `.claude/tools/plan-tracker/tracker.py` - Existing state mutation model.
  - `.claude/commands/dev-sdd-start-work.md` - Must remain compatible with plan precedence after redefine.
  - `README.md` - User-facing command narrative that may need compatibility notes.

  **Acceptance Criteria**:
  - [ ] REDEFINE contract names upstream inputs and downstream regenerated artifacts.
  - [ ] REDEFINE preserves `plan.json` as authority.
  - [ ] Tests cover changed-plan propagation and legacy-name compatibility behavior.

  **QA Scenarios**:
  ```text
  Scenario: REDEFINE updates derived artifacts while preserving plan.json authority
    Tool: Bash
    Preconditions: Fixture `skill-tests/fixtures/redefine/plan-change-project/` has seeded `plan.json` and generated docs
    Steps:
      1. Run `python3 .claude/tools/redefine/run.py skill-tests/fixtures/redefine/plan-change-project --json --dry-run | tee .sisyphus/evidence/task-7-redefine-propagation.txt`
      2. Run `python3 -m pytest skill-tests/cases/test_redefine_tool.py -k propagates_plan_updates -q | tee -a .sisyphus/evidence/task-7-redefine-propagation.txt`
      3. Assert output shows `plan.json` as the updated source before derived docs
    Expected Result: Helper exits 0 and pytest reports `1 passed`
    Failure Indicators: PLAN.md treated as source or undocumented changes
    Evidence: .sisyphus/evidence/task-7-redefine-propagation.txt

  Scenario: REDEFINE handles legacy REDEFIND alias safely
    Tool: Bash
    Preconditions: Alias behavior is implemented/documented
    Steps:
      1. Run `python3 .claude/tools/redefine/run.py --alias REDEFIND skill-tests/fixtures/redefine/plan-change-project --json --dry-run | tee .sisyphus/evidence/task-7-redefine-alias.txt`
      2. Run `python3 -m pytest skill-tests/cases/test_redefine_tool.py -k legacy_alias -q | tee -a .sisyphus/evidence/task-7-redefine-alias.txt`
      3. Assert output contains an alias notice and routes to REDEFINE semantics
    Expected Result: Alias path works and pytest reports `1 passed`
    Failure Indicators: Duplicate implementation path or alias failure
    Evidence: .sisyphus/evidence/task-7-redefine-alias.txt
  ```

  **Commit**: YES
  - Message: `feat(redefine): define propagation and resync flow`
  - Files: command doc, helper backend, tests
  - Pre-commit: targeted tests for REDEFINE

- [x] 8. Specify `DEV_SDD:UPDATE_TODO` stable-ID merge flow

  **What to do**:
  - Define the TODO data model with stable task IDs and merge semantics.
  - Support partial updates, conflict detection, preservation of user edits, and interactive confirmation for changed items.
  - Define how TODO items map back to `plan.json` entities and how untouched manual notes remain intact.

  **Must NOT do**:
  - Do not rewrite the full TODO file when only a subset changes.
  - Do not lose user-authored content or reorder tasks unpredictably.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Merge semantics, ID stability, and conflict handling are logic-heavy.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `writing`: merge mechanics dominate.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with 6, 7, 9, 10)
  - **Blocks**: 11, 12, 13
  - **Blocked By**: 2, 3, 4, 5

  **References**:
  - `docs/TODO.md` - Framework guidance that should describe but not override project TODO behavior.
  - `.claude/tools/plan-tracker/tracker.py` - Existing state fields to map from.
  - `.claude/tools/start-work/run.py` - Next-action logic that TODO reconciliation must feed.
  - `skill-tests/generated/cases.json:501-505` - Existing TODO-state expectations that should remain representable.

  **Acceptance Criteria**:
  - [ ] TODO item IDs are stable and documented.
  - [ ] Partial update flow can update only selected items.
  - [ ] Tests cover preserved manual edits, changed item confirmation, and no-op updates.

  **QA Scenarios**:
  ```text
  Scenario: UPDATE_TODO partially updates matching task IDs only
    Tool: Bash
    Preconditions: Fixture `skill-tests/fixtures/update_todo/partial-merge-project/` contains multiple task IDs and manual notes
    Steps:
      1. Run `python3 .claude/tools/update-todo/run.py skill-tests/fixtures/update_todo/partial-merge-project --ids T-002,T-004 --json --dry-run | tee .sisyphus/evidence/task-8-update-todo-partial.txt`
      2. Run `python3 -m pytest skill-tests/cases/test_update_todo_tool.py -k partial_merge_by_id -q | tee -a .sisyphus/evidence/task-8-update-todo-partial.txt`
      3. Assert output lists only `T-002` and `T-004` and preserves the manual notes block
    Expected Result: Helper exits 0 and pytest reports `1 passed`
    Failure Indicators: Full-file rewrite or lost user content
    Evidence: .sisyphus/evidence/task-8-update-todo-partial.txt

  Scenario: UPDATE_TODO pauses for confirmation on conflicting local edits
    Tool: Bash
    Preconditions: Fixture `skill-tests/fixtures/update_todo/conflict-project/` has a locally edited item with the same ID
    Steps:
      1. Run `python3 .claude/tools/update-todo/run.py skill-tests/fixtures/update_todo/conflict-project --ids T-003 --json --dry-run | tee .sisyphus/evidence/task-8-update-todo-conflict.txt`
      2. Run `python3 -m pytest skill-tests/cases/test_update_todo_tool.py -k conflicting_edit_requires_confirmation -q | tee -a .sisyphus/evidence/task-8-update-todo-conflict.txt`
      3. Assert output returns conflict metadata for `T-003`
    Expected Result: No overwrite without confirmation and pytest reports `1 passed`
    Failure Indicators: Silent overwrite or missing conflict payload
    Evidence: .sisyphus/evidence/task-8-update-todo-conflict.txt
  ```

  **Commit**: YES
  - Message: `feat(todo): define stable-id merge flow`
  - Files: command doc, helper backend, tests
  - Pre-commit: targeted tests for UPDATE_TODO

- [x] 9. Enhance `DEV_SDD:START_WORK` with TODO reconciliation

  **What to do**:
  - Extend START_WORK semantics so it loads project memory/session state, inspects unfinished project `docs/TODO.md` items, reconciles them against `plan.json`, and returns the next actionable work item.
  - Define mismatch behavior when TODO and plan disagree.
  - Preserve existing session/handoff precedence and degrade gracefully.

  **Must NOT do**:
  - Do not make TODO the sole execution truth.
  - Do not break current `start-work/run.py` JSON contract.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: This touches workflow selection, reconciliation logic, and backward compatibility.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `writing`: behavior logic is primary.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with 6, 7, 8, 10)
  - **Blocks**: 11, 12, 13
  - **Blocked By**: 2, 3, 4, 5

  **References**:
  - `.claude/commands/dev-sdd-start-work.md` - Existing command contract to extend.
  - `.claude/tools/start-work/run.py:207-299` - Current plan/session detection and precedence logic.
  - `README.md:145-163` - Public description of start-work behavior.
  - `projects/_template/CLAUDE.md:40-43` - Project docs load-map referencing current progress and session files.

  **Acceptance Criteria**:
  - [ ] START_WORK explicitly reconciles project TODO state against `plan.json`.
  - [ ] Conflict cases produce deterministic output and next-step guidance.
  - [ ] Tests cover TODO aligned, TODO stale, and no-TODO cases.

  **QA Scenarios**:
  ```text
  Scenario: START_WORK chooses next action from reconciled plan+todo state
    Tool: Bash
    Preconditions: Fixture project `skill-tests/fixtures/start_work/todo-aligned-project/` has `plan.json` plus TODO with a matching unfinished item
    Steps:
      1. Run `python3 .claude/tools/start-work/run.py skill-tests/fixtures/start_work/todo-aligned-project --json | tee .sisyphus/evidence/task-9-start-work-reconciled.json`
      2. Run `python3 -m pytest skill-tests/cases/test_start_work_tool.py -k reconciles_todo_with_plan -q | tee -a .sisyphus/evidence/task-9-start-work-reconciled.json`
      3. Assert saved JSON contains `status`, `message`, `data.plan`, and a deterministic `next_action`
    Expected Result: Helper exits 0 and pytest reports `1 passed`
    Failure Indicators: Missing next_action, invalid JSON, TODO-only decision path
    Evidence: .sisyphus/evidence/task-9-start-work-reconciled.json

  Scenario: START_WORK detects TODO/plan mismatch and warns before proceeding
    Tool: Bash
    Preconditions: Fixture project `skill-tests/fixtures/start_work/todo-mismatch-project/` has a stale TODO item not matching `plan.json`
    Steps:
      1. Run `python3 .claude/tools/start-work/run.py skill-tests/fixtures/start_work/todo-mismatch-project --json | tee .sisyphus/evidence/task-9-start-work-mismatch.json`
      2. Run `python3 -m pytest skill-tests/cases/test_start_work_tool.py -k warns_on_todo_plan_mismatch -q | tee -a .sisyphus/evidence/task-9-start-work-mismatch.json`
      3. Assert JSON `status` is `warning` or the message contains reconciliation guidance
    Expected Result: Tool degrades gracefully and pytest reports `1 passed`
    Failure Indicators: Silent mismatch acceptance or crash
    Evidence: .sisyphus/evidence/task-9-start-work-mismatch.json
  ```

  **Commit**: YES
  - Message: `feat(start-work): reconcile todo against plan`
  - Files: command doc, helper backend, tests
  - Pre-commit: targeted tests for START_WORK

- [x] 10. Specify `DEV_SDD:FIX` triage and optioning flow

  **What to do**:
  - Define a fix workflow that loads project memory/module status first, analyzes impact, and then presents two options: minimal-change and comprehensive-change.
  - Define required inputs (issue description, optional repro, module hints) and fallback discovery behavior.
  - Define how new bug learnings are eligible for memory sedimentation after resolution.

  **Must NOT do**:
  - Do not jump straight into implementation without impact analysis.
  - Do not present options without risk/regression notes.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Triage workflow spans memory, impact analysis, and action presentation.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `diagnose-bug`: execution-phase skill, not planning output itself.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with 6, 7, 8, 9)
  - **Blocks**: 11, 12, 13
  - **Blocked By**: 4, 5

  **References**:
  - `projects/structured-light-stereo/CLAUDE.md` - Example active-project context entrypoint the fix flow should read before proposing changes.
  - `projects/structured-light-stereo/memory/INDEX.md` - Example project-memory index the fix flow should consult before proposing changes.
  - `AGENTS.md:64-80` - Existing skill/hook landscape for bug workflows.
  - `README.md` - Public workflow narrative that may mention fix/debug practices.
  - External reference summary in draft - Bug triage should precede change selection.

  **Acceptance Criteria**:
  - [ ] FIX contract requires project/context inspection before recommending changes.
  - [ ] It always presents minimal and comprehensive options with trade-offs.
  - [ ] Tests cover missing repro input, localized bug, and high-impact bug cases.

  **QA Scenarios**:
  ```text
  Scenario: FIX produces both option tiers after project-context inspection
    Tool: Bash
    Preconditions: Fixture issue input `skill-tests/fixtures/fix/repro-issue.json` and project memory fixture exist
    Steps:
      1. Run `python3 .claude/tools/fix/run.py skill-tests/fixtures/fix/repro-issue.json --json --dry-run | tee .sisyphus/evidence/task-10-fix-options.txt`
      2. Run `python3 -m pytest skill-tests/cases/test_fix_tool.py -k emits_dual_repair_options -q | tee -a .sisyphus/evidence/task-10-fix-options.txt`
      3. Assert output includes a memory/context summary plus `minimal-change` and `comprehensive-change`
    Expected Result: Helper exits 0 and pytest reports `1 passed`
    Failure Indicators: Only one option, no context inspection, or no trade-offs
    Evidence: .sisyphus/evidence/task-10-fix-options.txt

  Scenario: FIX handles sparse issue reports gracefully
    Tool: Bash
    Preconditions: Issue input fixture `skill-tests/fixtures/fix/sparse-issue.json` omits repro details
    Steps:
      1. Run `python3 .claude/tools/fix/run.py skill-tests/fixtures/fix/sparse-issue.json --json --dry-run | tee .sisyphus/evidence/task-10-fix-sparse-input.txt`
      2. Run `python3 -m pytest skill-tests/cases/test_fix_tool.py -k sparse_issue_requires_more_context -q | tee -a .sisyphus/evidence/task-10-fix-sparse-input.txt`
      3. Assert output requests missing data or marks confidence low without crashing
    Expected Result: Helper exits 0 and pytest reports `1 passed`
    Failure Indicators: Crash, blind solution recommendation, or missing caution
    Evidence: .sisyphus/evidence/task-10-fix-sparse-input.txt
  ```

  **Commit**: YES
  - Message: `feat(fix): define triage and option flow`
  - Files: command doc, helper backend, tests
  - Pre-commit: targeted tests for FIX

- [x] 11. Unify CLI wiring and JSON output contracts

  **What to do**:
  - Add or align helper CLI entrypoints so the five commands share consistent machine-readable outputs, root detection, and target-project resolution.
  - Reuse existing helper patterns instead of introducing divergent entrypoints.
  - Resolve historical inconsistencies across tools where output or project-root logic differs.

  **Must NOT do**:
  - Do not fork separate incompatible command runners.
  - Do not leave root-detection behavior inconsistent across start-work, plan-tracker, and new helpers.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Cross-tool integration and compatibility work.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `quick`: too broad and cross-cutting for trivial treatment.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3)
  - **Blocks**: 12, 13
  - **Blocked By**: 6, 7, 8, 9, 10

  **References**:
  - `.claude/tools/start-work/run.py` - Existing helper baseline.
  - `.claude/tools/plan-tracker/tracker.py` - Existing project/root resolution gap source.
  - `.claude/tools/sdd-cli/cli.py` - Existing CLI output contract and command-dispatch style.
  - `.claude/commands/*.md` - Slash-command docs that should point to the unified backend behavior.

  **Acceptance Criteria**:
  - [ ] New and existing helpers share consistent `{status,message,data}` output.
  - [ ] Target-project resolution is consistent across tools.
  - [ ] Tests cover execution from framework root and nested project paths.

  **QA Scenarios**:
  ```text
  Scenario: CLI helpers produce consistent JSON envelopes
    Tool: Bash
    Preconditions: Updated helper commands exist
    Steps:
      1. Run `python3 -m pytest skill-tests/cases/test_workflow_cli_contracts.py -k json_envelope_consistency -q | tee .sisyphus/evidence/task-11-cli-envelope.txt`
      2. Assert the test checks `.claude/tools/init/run.py`, `.claude/tools/redefine/run.py`, `.claude/tools/update-todo/run.py`, `.claude/tools/start-work/run.py`, and `.claude/tools/fix/run.py`
    Expected Result: Pytest reports `1 passed`
    Failure Indicators: Missing keys, inconsistent shapes, invalid JSON
    Evidence: .sisyphus/evidence/task-11-cli-envelope.txt

  Scenario: Root detection works from multiple working directories
    Tool: Bash
    Preconditions: Test harness can invoke helpers from root and subdirectories
    Steps:
      1. Run `python3 -m pytest skill-tests/cases/test_workflow_cli_contracts.py -k project_resolution_is_stable -q | tee .sisyphus/evidence/task-11-root-detection.txt`
      2. Assert the test covers invocation from repo root and a nested project path
    Expected Result: Pytest reports `1 passed`
    Failure Indicators: `unknown` project drift or path mismatches
    Evidence: .sisyphus/evidence/task-11-root-detection.txt
  ```

  **Commit**: YES
  - Message: `feat(cli): unify workflow helper contracts`
  - Files: `.claude/tools/**/*`, command docs
  - Pre-commit: helper JSON contract tests

- [x] 12. Add regression and lint guardrails against workflow drift

  **What to do**:
  - Add tests and checks that catch template residue, markdown-first regressions, TODO overwrite mistakes, and inconsistent command outputs.
  - Ensure new rules integrate into existing repo validation habits (`skill-tests`, targeted tests, helper checks).
  - Add explicit regression cases for historical issues discovered in this audit.

  **Must NOT do**:
  - Do not rely on manual review to catch plan ownership drift.
  - Do not add guardrails that only work for one project fixture.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Requires translating audit findings into enforceable regression coverage.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `writing`: guardrail design is logic/test heavy.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3 with 13 after 11)
  - **Blocks**: FINAL
  - **Blocked By**: 6, 7, 8, 9, 10, 11

  **References**:
  - `skill-tests/cases/test_start_work_tool.py` - Existing start-work regression suite.
  - `skill-tests/generated/cases.json` - Existing workflow-behavior expectations touching TODO and stuck states.
  - `.claude/tools/plan-tracker/tracker.py` - Source-of-truth guard conditions.
  - Audit findings in draft/plan - Historical drift cases to encode as tests.

  **Acceptance Criteria**:
  - [ ] Regression tests fail if placeholders reappear in root docs.
  - [ ] Regression tests fail if `PLAN.md` reclaims execution-source ownership.
  - [ ] Regression tests fail if UPDATE_TODO overwrites user edits without confirmation.

  **QA Scenarios**:
  ```text
  Scenario: Regression suite catches workflow-drift failures
    Tool: Bash
    Preconditions: New tests are added
    Steps:
      1. Run `python3 -m pytest skill-tests/cases/test_workflow_drift_guards.py -q | tee .sisyphus/evidence/task-12-regression-suite.txt`
      2. Capture pass/fail counts and the exact drift-guard test names
    Expected Result: Pytest reports all drift guards passing
    Failure Indicators: Any drift case failing or missing from output
    Evidence: .sisyphus/evidence/task-12-regression-suite.txt

  Scenario: Negative fixture proves overwrite guard is enforced
    Tool: Bash
    Preconditions: Test harness contains conflict fixture
    Steps:
      1. Before implementation, run `python3 -m pytest skill-tests/cases/test_update_todo_tool.py -k conflicting_edit_requires_confirmation -q | tee .sisyphus/evidence/task-12-overwrite-guard-red.txt || true`
      2. Assert `.sisyphus/evidence/task-12-overwrite-guard-red.txt` contains `FAILED` or `AssertionError`
      3. After implementation, rerun `python3 -m pytest skill-tests/cases/test_update_todo_tool.py -k conflicting_edit_requires_confirmation -q | tee .sisyphus/evidence/task-12-overwrite-guard-green.txt`
      4. Assert `.sisyphus/evidence/task-12-overwrite-guard-green.txt` contains `1 passed`
    Expected Result: Explicit RED and GREEN evidence exists for overwrite protection
    Failure Indicators: Missing RED capture, missing GREEN pass, or guardrail still absent
    Evidence: .sisyphus/evidence/task-12-overwrite-guard-red.txt, .sisyphus/evidence/task-12-overwrite-guard-green.txt
  ```

  **Commit**: YES
  - Message: `test(workflow): add drift regression guards`
  - Files: tests, lint/check scripts as needed
  - Pre-commit: targeted regression suite

- [x] 13. Write migration and rollout guidance

  **What to do**:
  - Document how existing repositories and the framework root move from mixed markdown-first behavior to `plan.json`-centric behavior.
  - Include migration steps for root docs, project templates, command aliases, TODO IDs, and START_WORK expectations.
  - Document compatibility expectations and rollback strategy.

  **Must NOT do**:
  - Do not leave existing users guessing how to adopt the new commands.
  - Do not omit legacy behavior notes where command or doc semantics changed.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: This is rollout/migration documentation with explicit adoption steps.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `deep`: integration logic already decided upstream.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3)
  - **Blocks**: FINAL
  - **Blocked By**: 1, 2, 3, 5, 7, 8, 9, 10, 11

  **References**:
  - `README.md` - Public user-facing workflow docs requiring updates.
  - `docs/CONTEXT.md`, `docs/PLAN.md`, `docs/TODO.md` - New framework-level doc model.
  - `.claude/commands/*.md` - Command surface requiring migration notes.
  - `.claude/tools/start-work/run.py` and `.claude/tools/plan-tracker/tracker.py` - Tooling behavior that rollout docs must explain.

  **Acceptance Criteria**:
  - [ ] Migration guidance explains old vs new ownership rules clearly.
  - [ ] Rollout steps cover framework root, project templates, and active projects.
  - [ ] Rollback/compatibility notes are explicit.

  **QA Scenarios**:
  ```text
  Scenario: Migration doc covers all changed command/workflow surfaces
    Tool: Bash
    Preconditions: Migration docs are written
    Steps:
      1. Run `python3 -m pytest skill-tests/cases/test_workflow_migration_docs.py -k coverage_of_changed_surfaces -q | tee .sisyphus/evidence/task-13-migration-coverage.txt`
      2. Run `python3 - <<'PY'
from pathlib import Path
text = Path('README.md').read_text() if Path('README.md').exists() else ''
targets = ['INIT','REDEFINE','UPDATE_TODO','START_WORK','FIX','plan.json','TODO']
for t in targets:
    assert t in text or t.lower() in text.lower()
PY`
      3. Save terminal output
    Expected Result: Pytest reports `1 passed` and the inline check exits 0
    Failure Indicators: Missing command/workflow guidance
    Evidence: .sisyphus/evidence/task-13-migration-coverage.txt

  Scenario: Rollout notes include fallback or rollback guidance
    Tool: Bash
    Preconditions: Migration docs are written
    Steps:
      1. Run `python3 -m pytest skill-tests/cases/test_workflow_migration_docs.py -k includes_rollback_guidance -q | tee .sisyphus/evidence/task-13-rollout-safety.txt`
      2. Run `python3 - <<'PY'
from pathlib import Path
text = Path('README.md').read_text().lower() if Path('README.md').exists() else ''
assert 'rollback' in text or 'compatibility' in text or 'fallback' in text
PY`
      3. Save terminal output
    Expected Result: Pytest reports `1 passed` and inline check exits 0
    Failure Indicators: No rollout safety guidance
    Evidence: .sisyphus/evidence/task-13-rollout-safety.txt
  ```

  **Commit**: YES
  - Message: `docs(migration): add workflow rollout guidance`
  - Files: `README.md`, related docs/command docs
  - Pre-commit: documentation coverage checks



## Final Verification Wave (MANDATORY — after ALL implementation tasks)

- [x] F1. **Plan Compliance Audit** — `oracle`
  Verify root docs are framework-scoped, project execution remains `plan.json`-centric, command flows match this plan, and evidence files exist.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT`

  **QA Scenario**:
  ```text
  Tool: Bash
  Steps:
    1. Run `python3 - <<'PY'
from pathlib import Path
checks = {
  'docs/CONTEXT.md': ['framework', 'projects/<PROJECT>/docs'],
  'docs/PLAN.md': ['plan.json', 'source of truth'],
  'docs/TODO.md': ['framework', 'project'],
  '.claude/commands/dev-sdd-start-work.md': ['plan.json', 'PLAN.md', 'IMPLEMENTATION_PLAN.md'],
}
for file, needles in checks.items():
    text = Path(file).read_text()
    for needle in needles:
        assert needle.lower() in text.lower(), (file, needle)
PY`
    2. Run `python3 -m pytest skill-tests/cases/test_init_tool.py skill-tests/cases/test_redefine_tool.py skill-tests/cases/test_update_todo_tool.py skill-tests/cases/test_start_work_tool.py skill-tests/cases/test_fix_tool.py -q | tee .sisyphus/evidence/final-qa/f1-plan-compliance.txt`
  Expected Result: Inline audit exits 0 and pytest reports all targeted command tests passing
  Evidence: .sisyphus/evidence/final-qa/f1-plan-compliance.txt
  ```

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run repo tests/lint relevant to changed files, inspect for duplicated logic, stale placeholders, manual-edit drift, and inconsistent JSON output contracts.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

  **QA Scenario**:
  ```text
  Tool: Bash
  Steps:
    1. Run `python3 -m pytest skill-tests/cases/test_workflow_cli_contracts.py skill-tests/cases/test_workflow_drift_guards.py skill-tests/cases/test_workflow_migration_docs.py -q | tee .sisyphus/evidence/final-qa/f2-code-quality.txt`
    2. Run `python3 skill-tests/run_all.py | tee -a .sisyphus/evidence/final-qa/f2-code-quality.txt`
    3. Run `python3 - <<'PY'
from pathlib import Path
targets = ['docs/CONTEXT.md','docs/PLAN.md','docs/TODO.md']
for f in targets:
    text = Path(f).read_text()
    assert '{{' not in text and '}}' not in text
PY`
  Expected Result: All tests pass and no root docs contain unresolved placeholders
  Evidence: .sisyphus/evidence/final-qa/f2-code-quality.txt
  ```

- [x] F3. **Real QA Execution** — `unspecified-high`
  Execute command scenarios for INIT, REDEFINE, UPDATE_TODO, START_WORK, and FIX against fixtures or test projects, capturing evidence under `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

  **QA Scenario**:
  ```text
  Tool: Bash
  Steps:
    1. Run `python3 .claude/tools/init/run.py skill-tests/fixtures/init/empty-project --json --dry-run | tee .sisyphus/evidence/final-qa/f3-init.json`
    2. Run `python3 .claude/tools/redefine/run.py skill-tests/fixtures/redefine/plan-change-project --json --dry-run | tee .sisyphus/evidence/final-qa/f3-redefine.json`
    3. Run `python3 .claude/tools/update-todo/run.py skill-tests/fixtures/update_todo/partial-merge-project --ids T-002,T-004 --json --dry-run | tee .sisyphus/evidence/final-qa/f3-update-todo.json`
    4. Run `python3 .claude/tools/start-work/run.py skill-tests/fixtures/start_work/todo-aligned-project --json | tee .sisyphus/evidence/final-qa/f3-start-work.json`
    5. Run `python3 .claude/tools/fix/run.py skill-tests/fixtures/fix/repro-issue.json --json --dry-run | tee .sisyphus/evidence/final-qa/f3-fix.json`
  Expected Result: All commands emit valid JSON envelopes and fixture-specific expected fields
  Evidence: .sisyphus/evidence/final-qa/f3-command-execution.txt
  ```

- [x] F4. **Scope Fidelity Check** — `deep`
  Compare final diff and behavior against this plan; reject any markdown-first regression, missing merge protections, or undocumented workflow changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

  **QA Scenario**:
  ```text
  Tool: Bash
  Steps:
    1. Run `python3 - <<'PY'
from pathlib import Path
plan = Path('.sisyphus/plans/dev-sdd-agent-optimization.md').read_text()
required = [
  'plan.json remains the execution source of truth',
  'stable-ID merge flow',
  'TODO reconciliation',
  'minimal-change and comprehensive-change',
]
for needle in required:
    assert needle in plan
PY`
    2. Run `python3 -m pytest skill-tests/cases/test_workflow_drift_guards.py -q | tee .sisyphus/evidence/final-qa/f4-scope-fidelity.txt`
  Expected Result: Plan invariants remain represented and drift-guard tests pass
  Evidence: .sisyphus/evidence/final-qa/f4-scope-fidelity.txt
  ```

---

## Commit Strategy

- **1**: `docs(framework): redefine root context ownership`
- **2**: `docs(framework): redefine plan and todo models`
- **3**: `docs(template): align project template with plan-json workflow`
- **4**: `feat(commands): add init redefine update-todo fix contracts`
- **5**: `feat(start-work): reconcile todo with plan state`
- **6**: `test(workflow): cover command flows and drift guards`
- **7**: `docs(migration): add rollout and compatibility guidance`

---

## Success Criteria

### Verification Commands
```bash
python3 .claude/tools/start-work/run.py --json
python3 .claude/tools/plan-tracker/tracker.py status --json
python3 skill-tests/run_all.py
```

### Final Checklist
- [ ] All root framework docs are instantiated and consistent
- [ ] `plan.json` ownership is explicit and enforced
- [ ] TODO merge/update behavior preserves user edits
- [ ] START_WORK reconciles TODO, plan, memory, and session state
- [ ] FIX offers both minimal and comprehensive options
- [ ] Automated tests pass for new and historical workflow cases
