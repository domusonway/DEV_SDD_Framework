# HOOK: post-green
> 触发时机：所有测试变为 GREEN 后，立即执行

---

## 执行步骤

### Step 1: 运行 validate-output skill
```
读取 .claude/skills/validate-output/SKILL.md 并完整执行
```

### Step 2: 运行 post-green 脚本
```bash
bash .claude/hooks/post-green/run.sh
```

### Step 3: 记忆沉淀判断
检查本轮实现中是否有值得记录的经验：
- 遇到过 RED > 2 次的 Bug？→ 必须记录
- 有超出预期的设计决策？→ 建议记录
- 发现 SPEC 不清晰的地方？→ 记录并更新 SPEC

执行：读取 `.claude/skills/memory-update/SKILL.md`

### Step 4: 输出完成报告
```
[POST-GREEN 完成]
测试状态：X/X PASS
验收结果：✅ / ⚠️ [细节]
记忆沉淀：N条新记忆写入 projects/<n>/memory/
下一步：[继续下一模块 / 项目交付]
```
