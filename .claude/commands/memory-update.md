# /project:memory-update — 手动触发记忆沉淀

## 用法
```
/project:memory-update
```

## 执行步骤
1. 读取并执行 `.claude/skills/memory-update/SKILL.md` 完整流程
2. 执行 `.claude/agents/meta-skill-agent.md` 生成框架改进候选
3. 执行 `bash .claude/hooks/verify-rules/check_tools.sh ${PROJECT}` 工具健康检测
4. 输出候选摘要并提示运行 `/project:skill-review`

## 适用场景
- 项目里程碑完成后（不一定等到全部完成）
- 遇到重要 Bug 修复后，及时记录
- 发现某个框架记忆条目有误，需要更新
- **手动触发 Meta-Skill Loop 扫描**

## 与 post-green hook 的区别
post-green 是自动触发（每次测试变绿），memory-update 是手动按需触发，
可在任何时间点执行。两者的 Meta-Skill Agent 扫描范围相同，但 memory-update
会做更完整的跨 session 历史扫描。

## 与 /project:skill-review 的关系
memory-update 负责**生成**候选（写入 candidates/）；
skill-review 负责**审核和提升**候选（写入目标框架文件）。
两者配合完成完整的 Meta-Skill Loop。
