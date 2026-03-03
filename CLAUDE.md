# SDD Framework — Agent-Driven Project Reconstruction

> 通用框架层。项目特有内容在 `projects/<your_project>/CLAUDE.md` 中维护。

## 框架核心约束（适用于所有项目）
1. **不复制参考代码** — 复制跳过理解过程，重构失去意义
2. **测试失败只改实现** — 改测试掩盖问题，集成阶段以更难诊断的形式爆发
3. **先写 SPEC 再写代码** — 没有规格的实现无法被验证，也无法被其他 Agent 接手

## 框架结构导航
- 框架经验索引：@memory/INDEX.md
- 全局规划模板：@docs/architecture/PLAN.md
- 全局任务模板：@docs/architecture/TODO.md
- 新建项目指南：@docs/HOW_TO_START_PROJECT.md

## Agent 与 Skills（框架内置）
- 分析参考项目/制定规划 → `@planner`
- TDD 实现功能模块 → `@implementer`
- 生成 fixtures/运行校验 → `@tester`
- 代码复审 → `@reviewer`
- 生产 Bug 诊断修复 → `@diagnostician`
- Skills 由 Claude 根据任务自动调用（model-invoked）

## ⚠️ 启动新项目前必读
@docs/HOW_TO_START_PROJECT.md
