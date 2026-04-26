# sub_docs

`docs/sub_docs/` stores project task details. `docs/plan.json` remains the execution source of truth.

Standard directories:

| Directory | Template IDs | Purpose |
|---|---|---|
| `analysis/` | `problem-analysis` | Issue triage, root cause and risk analysis |
| `architecture/` | `architecture-overview` | Project structure, module boundaries, data flow |
| `bug/` | `problem-analysis` | Bug-specific diagnosis, fix and regression notes |
| `decisions/` | `decision-record` | Decision records and trade-offs |
| `feature/` | `implementation-brief` | Feature/task design and implementation details |
| `reports/` | `project-status-review`, `review-report` | Project status, review and closeout reports |
| `rules/` | `rule-guide` | Project-specific operating rules and guides |
| `validation/` | `module-validation-report` | Module validation reports and evidence |

Use `python3 .claude/tools/doc-template/run.py classify "<task>" --json` before creating new documents.
