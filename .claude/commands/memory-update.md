# /project:memory-update — 手动触发记忆沉淀

## 用法
```
/project:memory-update
```

## 执行步骤
读取并执行 `.claude/skills/memory-update/SKILL.md` 完整流程。

## 适用场景
- 项目里程碑完成后（不一定等到全部完成）
- 遇到重要 Bug 修复后，及时记录
- 发现某个框架记忆条目有误，需要更新

## 与 post-green hook 的区别
post-green 是自动触发，memory-update 是手动按需触发，可在任何时间点执行。
