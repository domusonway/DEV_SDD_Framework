---
id: module-validation-report
version: 1.0
scope: project_sub_doc
intent_keywords: 模块验证,单模块,功能验证,流程验证,性能,cli,上游输入,下游输出,审查报告,执行细节
default_dir: projects/<PROJECT>/docs/sub_docs/validation
filename_pattern: <module>-validation-report.md
required_sections: 摘要,验证目标,模块范围,入口路径,上游输入,下游输出,执行命令,结果摘要,详细证据,性能与稳定性,风险与缺口,下一步
language_policy: zh_cn_default_preserve_terms
---

# <TITLE>

## 摘要

<说明模块验证结论，明确 ok/warning/error。>

## 验证目标

- <目标 1：功能、流程、性能或在线使用要求。>

## 模块范围

- 模块：`<MODULE>`
- 代码路径：`<CODE_PATH>`
- 关联 SPEC/文档：`<SPEC_PATH>`

## 入口路径

| 入口 | 命令/调用方式 | 期望 |
|---|---|---|
| CLI | `<command>` | <expected> |
| adapter/contracts | `<path/function>` | <expected> |
| model upstream | `<input source>` | <expected> |

## 上游输入

<列出输入来源、字段、类型、样例和边界条件。>

## 下游输出

<列出输出对象、字段、类型、消费者和失败语义。>

## 执行命令

```bash
<command 1>
<command 2>
```

## 结果摘要

| 检查项 | 结果 | 证据 |
|---|---|---|
| 功能 | <ok/warning/error> | <path/report> |

## 详细证据

<逐条记录执行日志、文件路径、函数、输入输出样例和观察结果。>

## 性能与稳定性

<记录耗时、资源、并发/重复执行、失败重试或在线使用风险。>

## 风险与缺口

- <未覆盖路径、外部依赖、数据质量或上线风险。>

## 下一步

1. <下一模块或修复动作。>
