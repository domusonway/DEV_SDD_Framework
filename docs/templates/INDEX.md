# Doc Templates Index

| ID | Intent | Default Scope | Use Case |
|---|---|---|---|
| `problem-analysis` | 问题分析 / 根因定位 | project | 分析 bug、失败、风险和修复方案 |
| `architecture-overview` | 架构梳理 / 模块关系 | project_sub_doc | 梳理模块边界、数据流和关键契约 |
| `project-status-review` | 项目状态审查 | project | 汇总项目完成度、风险、下一步 |
| `module-validation-report` | 模块验证报告 | project_sub_doc | 从 CLI、上游输入、下游输出、性能等入口验证单模块 |
| `decision-record` | 决策记录 | project | 记录关键技术/流程决策和取舍 |
| `implementation-brief` | 功能/任务实现简报 | project_sub_doc | 进入实现前固化目标、接口、测试和验收 |
| `rule-guide` | 规则指引 / 操作规范 | project_sub_doc | 固化项目或框架规则、示例和维护方式 |
| `review-report` | 审查报告 | project_sub_doc | 记录审查发现、证据、风险评级和建议动作 |

## Directory Mapping

| sub_docs Directory | Template IDs |
|---|---|
| `analysis/` | `problem-analysis` |
| `architecture/` | `architecture-overview` |
| `bug/` | `problem-analysis` |
| `decisions/` | `decision-record` |
| `feature/` | `implementation-brief` |
| `reports/` | `project-status-review`, `review-report` |
| `rules/` | `rule-guide` |
| `validation/` | `module-validation-report` |

使用工具：

```bash
python3 .claude/tools/doc-template/run.py classify "写 runtime 模块验证报告" --json
python3 .claude/tools/doc-template/run.py scaffold module-validation-report --project agentplatform --module runtime --json
python3 .claude/tools/doc-template/run.py validate projects/agentplatform/docs/sub_docs/runtime-validation-report.md --template module-validation-report --json
```

## Language Policy

默认使用中文编写文档；专业术语、API 名称、代码标识符、命令、文件路径、协议字段和英文专有名词保持原文。
