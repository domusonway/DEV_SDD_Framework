---
id: review-report
version: 1.0
scope: project_sub_doc
intent_keywords: 审查报告,review report,复盘,质量审查,代码审查,文档审查,风险审查
default_dir: projects/<PROJECT>/docs/sub_docs/reports
filename_pattern: <topic>-review-report.md
required_sections: 摘要,审查范围,发现项,证据,风险评级,建议动作,验证命令
language_policy: zh_cn_default_preserve_terms
---

# <TITLE>

## 摘要

<说明审查结论。>

## 审查范围

<说明审查的文件、模块、命令、数据。>

## 发现项

| 严重级别 | 问题 | 位置 | 建议 |
|---|---|---|---|
| <high/medium/low> | | | |

## 证据

- <路径、命令、日志或测试结果。>

## 风险评级

<说明评级依据。>

## 建议动作

1. <下一步。>

## 验证命令

```bash
<验证命令>
```
