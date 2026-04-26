# sub_docs

`docs/sub_docs/` stores framework-level task details. Active project execution details belong under `projects/<PROJECT>/docs/sub_docs/`.

Standard directories:

| Directory | Template IDs | Purpose |
|---|---|---|
| `analysis/` | `problem-analysis` | Root cause analysis, issue triage, risk analysis |
| `architecture/` | `architecture-overview` | Framework structure, module/data-flow views |
| `bug/` | `problem-analysis` | Bug-specific analysis and regression notes |
| `decisions/` | `decision-record` | Decision records and trade-off notes |
| `feature/` | `implementation-brief` | Feature/task design and implementation details |
| `reports/` | `project-status-review`, `review-report` | Status, review, dashboard and closeout reports |
| `rules/` | `rule-guide` | Operating rules, usage guides and constraints |
| `validation/` | `module-validation-report` | Validation records and evidence |

Keep root docs framework-scoped. Do not place active project execution state here.
