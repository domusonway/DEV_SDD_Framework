# 全局任务追踪（TODO.md）

> 每次 Agent 执行后必须更新状态

## 阶段 0：框架初始化
- [x] CLAUDE.md 创建
- [x] .claude/skills/ 5个技能
- [x] .claude/agents/ 5个 subagent
- [x] .claude/hooks/ 4个 hook
- [x] .claude/settings.json
- [x] memory/ 结构化索引系统
- [x] modules/template/ 模板

## 阶段 1：参考项目分析（@planner）
- [ ] 分析参考项目结构
- [ ] 填写 docs/architecture/PLAN.md 模块表
- [ ] 填写依赖表

## 阶段 2：CONTEXT.md（@planner）
- [ ] projects/<proj>/CONTEXT.md §1-5 全部完成

## 阶段 3：模块 SPEC（@planner）
- [ ] M01 SPEC.md
- [ ] _(更多模块)_

## 阶段 4：Fixtures（@tester）
- [ ] generate_reference.py 各模块分支
- [ ] 各模块 reference pkl 生成
- [ ] 各模块校验器创建并自测

## 阶段 5：TDD 实现（@implementer）
- [ ] M01 TDD 完成 + 校验通过
- [ ] _(更多模块)_

## 阶段 6：集成测试
- [ ] python tests/run_all_validators.py 全部通过

## 🚨 阻塞项
_(无)_
