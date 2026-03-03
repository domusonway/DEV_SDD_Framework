---
name: spec-writer
description: |
  规格说明（SPEC）编写技能。当需要为新模块编写 SPEC.md、定义接口规格、
  分析参考项目接口、制定模块规格说明时自动调用。
  SDD 核心：先写规格，再写代码。规格是实现与测试的唯一约定。
  Use when creating new modules or documenting interfaces.
allowed-tools: Read, Write, Glob, Grep, Bash
agent: plan
---

# Spec 编写技能

## SPEC.md 必须包含的字段

```markdown
---
module: <name>
version: 0.1.0
status: draft | reviewed | locked
---

# 模块规格（SPEC.md）

## 1. 职责（单一职责原则，一句话）

## 2. 接口定义

### 函数签名
def <fn>(param: Type) -> ReturnType

### 输入规格
| 参数 | 类型 | dtype | 形状/格式 | 说明 |
|------|------|-------|----------|------|

### 输出规格  
| 返回 | 类型 | dtype | 形状/格式 | 说明 |
|------|------|-------|----------|------|
⚠️ dtype 必须明确（float32 vs float64 是最常见静默偏差来源）

## 3. 行为约束
- 输入验证（何时抛出什么异常）
- 边界条件（空输入、极值）
- 数值精度（dtype 要求）

## 4. 与参考项目对应（只记位置，不复制代码）
| 功能 | 参考位置 | 备注 |
|------|---------|------|

## 5. 测试要点
- 正常用例
- 边界用例
- 异常用例
- 输出比对基准：tests/fixtures/reference_<module>_output.pkl

## 6. 依赖
- 依赖模块：
- 被依赖于：
- 第三方库：
```

## 编写原则
- ✅ 描述"做什么"，不描述"怎么做"
- ✅ dtype 必须明确
- ❌ 不在 SPEC 里写算法步骤
- ❌ 不复制参考代码
