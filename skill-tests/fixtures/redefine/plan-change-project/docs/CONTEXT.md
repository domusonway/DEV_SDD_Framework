# Plan Change Project · 项目背景与架构

---

## 项目目标
验证 REDEFINE 以项目 CONTEXT 作为重定义输入，先更新 plan.json，再重建派生文档。

---

## 背景
该夹具模拟项目需求变更：`legacy_sync` 被移除，新增 `redefine_flow`。

---

## 技术栈
- 语言: Python 3.11
- 测试框架: pytest
- 主要依赖: stdlib only

---

## 模块划分

### capture_context
- 职责：采集并规范化项目上下文输入
- 输入：docs/CONTEXT.md
- 输出：结构化计划输入
- 依赖：无

### redefine_flow
- 职责：根据上下文变化重建计划并派生可读文档
- 输入：结构化计划输入
- 输出：docs/plan.json 与派生视图
- 依赖：capture_context

---

## 验收标准
- REDEFINE 先更新 `docs/plan.json`
- `docs/PLAN.md` 与 `docs/TODO.md` 来自最新 `plan.json`
