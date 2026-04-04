# Demo Init Project · 项目背景与架构

---

## 项目目标
建立一个最小 DEV_SDD 初始化样例，用于从项目 CONTEXT 自动生成引导文档和结构化计划。

---

## 背景
该项目只保留初始化所需的 `docs/CONTEXT.md`，其余入口文档应由 INIT 生成。

---

## 技术栈
- 语言: Python 3.11
- 测试框架: pytest
- 主要依赖: stdlib only

---

## 模块划分

### capture_context
- 职责：解析 CONTEXT.md 中的标题、目标和模块信息
- 输入：`docs/CONTEXT.md`
- 输出：结构化初始化元数据
- 依赖：无

### build_plan
- 职责：根据模块划分生成初始 `plan.json`
- 输入：结构化初始化元数据
- 输出：批次化执行计划
- 依赖：capture_context

---

## 验收标准
- INIT 生成 `plan.json` 并保持其为执行真相源
- INIT 为新项目生成入口文档而不读取 root `docs/*` 作为模板
