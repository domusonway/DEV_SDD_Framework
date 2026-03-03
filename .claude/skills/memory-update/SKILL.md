---
name: memory-update
description: |
  经验记忆更新技能。当遇到重要经验（成功/失败/Bug修复/环境问题）需要沉淀时调用。
  Use when completing a module, fixing a bug, or encountering a noteworthy pattern.
  触发词：记录经验、更新 memory、沉淀、经验总结。
allowed-tools: Read, Write, Edit, Glob
---

# Memory 更新技能

## 决策：写到哪里？

```
这条经验换个完全不同的项目还有用吗？
├── 是 → memory/framework/ 或 memory/domains/<domain>/
└── 否 → memory/projects/<project>/
```

## 记录格式（标准单条 MEM_*.md）

```markdown
---
id: MEM_<F|D|P>_<域>_<NNN>
title: <15字内精确标题>
tags:
  domain: general | <your_domain> | ...
  lang_stack: python | cpp | general
  task_type: tdd_impl | spec_writing | debugging | diagnosis
  severity: CRITICAL | IMPORTANT | TIPS
created: <YYYY-MM-DD>
expires: never | <YYYY-MM-DD>
confidence: high | medium | low
---

## 经验内容（200字内）

## 触发场景（什么情况该读此记录）

## 反例（错误做法 → 后果）

## 正例（正确做法，含代码示例）
```

## 创建后必须更新索引

```bash
# 更新 memory/INDEX.md 对应分类的表格，添加一行
# 更新对应域索引 memory/domains/<domain>/INDEX.md（如适用）
```

## 严重度说明
- **CRITICAL**：违反直接导致错误，永不过期，每次启动必加载
- **IMPORTANT**：提升效率，12个月后需 review
- **TIPS**：锦上添花，6个月后需 review
