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

### Step 3: Sedimentation Decision（不可跳过）
检查本轮实现中是否有值得记录的经验：
- 遇到过 RED > 2 次的 Bug？→ 必须记录
- 有超出预期的设计决策？→ 建议记录
- 发现 SPEC 不清晰的地方？→ 记录并更新 SPEC
- 新增了可复用的校验规则 / 启动边界约束 / 回归测试策略？→ 至少写 candidate 或项目 memory

执行：读取 `.claude/skills/memory-update/SKILL.md`，并显式输出 `no_sedimentation | project_memory | framework_candidate` 三选一决策。

### Step 4: 运行 hook-observer（新增）
```bash
python3 .claude/hooks/hook-observer/observe.py ${PROJECT}
```
检测本模块实现过程中是否存在 Hook 漏触发信号，生成 HOOK_CAND 候选。

### Step 5: 运行 tool health check（新增）
```bash
bash .claude/hooks/verify-rules/check_tools.sh ${PROJECT}
```
TOOL_SIGNAL 输出写入当前 session，供 meta-skill-agent 后续读取。

### Step 6: 输出完成报告
```
[POST-GREEN 完成]
测试状态：X/X PASS
验收结果：✅ / ⚠️ [细节]
沉淀决策：<no_sedimentation | project_memory | framework_candidate>
记忆动作：<无 / N条新记忆写入 projects/<n>/memory/ / N条候选写入 memory/candidates/>
hook-observer：[无候选 / N条候选写入 candidates/]
tool-health：[正常 / N个警告，见 TOOL_SIGNAL]
下一步：[继续下一模块 / 项目交付]
```
