# SKILL: complexity-assess
> 任务：在开始任何开发任务前，评估复杂度并决定工作模式

---

## 触发时机
收到开发任务后，**第一步**，读取此 SKILL，执行评估。

---

## 评分维度（共 10 分）

| 维度 | 0分 | 1分 | 2分 |
|------|-----|-----|-----|
| 模块数量 | 1个 | 2-3个 | 4个+ |
| 外部依赖 | 无 | stdlib only | 第三方库 |
| 并发要求 | 无 | 单线程 | 多线程/异步 |
| 状态管理 | 无状态 | 简单状态 | 复杂状态机 |
| 测试层级 | 单元 | 单元+集成 | 单元+集成+E2E |

---

## 模式判定

| 总分 | 模式 | 文档要求 | 流程 |
|------|------|---------|------|
| 0–3  | **L 轻量** | BRIEF.md ≤15行 | 直接 TDD |
| 4–7  | **M 标准** | CONTEXT.md + 各模块 SPEC.md | 规划 → TDD 逐模块 |
| 8+   | **H 完整** | 完整文档套件 + Agent 流水线 | Planner → Implementer → Reviewer |

---

## 执行步骤

### L 模式
1. 写 BRIEF.md（目标/接口/验收标准，≤15行）
2. 读取 `.claude/skills/tdd-cycle/SKILL.md` 开始实现

### M 模式
1. 写 docs/CONTEXT.md（背景、架构、模块划分）
2. 为每个模块写 modules/<name>/SPEC.md
3. 在 plan.json 中为模块显式区分 `spec_path` 与 `impl_path`
4. 按依赖顺序逐模块读取 tdd-cycle/SKILL.md 实现

### H 模式
1. 写完整文档套件（CONTEXT.md + PLAN.md + TODO.md + 所有 SPEC.md）
2. 读取 `.claude/agents/planner.md` 生成实现批次
3. 按批次调用 implementer → reviewer → memory-keeper

---

## 输出格式
```
复杂度评估
维度得分：模块=X, 依赖=X, 并发=X, 状态=X, 测试=X
总分：X/10
工作模式：[L/M/H]
下一步：[具体动作]
```
