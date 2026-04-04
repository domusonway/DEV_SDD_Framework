# Existing Docs Project · 项目背景与架构

---

## 项目目标
验证 INIT 在已有用户可见文档存在时返回确认元数据，而不是直接覆盖。

---

## 背景
该项目模拟已经由用户手工编辑过 `CLAUDE.md`、`README.md`、`docs/PLAN.md` 和 `docs/plan.json` 的情况。

---

## 技术栈
- 语言: Python 3.11
- 测试框架: pytest
- 主要依赖: stdlib only

---

## 模块划分

### preserve_user_docs
- 职责：在初始化时检查已有文档并返回 overwrite confirmation metadata
- 输入：已有项目目录
- 输出：结构化冲突列表
- 依赖：无

---

## 验收标准
- 已存在目标文档时，INIT 返回 confirmation-required 信息
- 未提供确认元数据前，任何现有文件都不会被覆盖
