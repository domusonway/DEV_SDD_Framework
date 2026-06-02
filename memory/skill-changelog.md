# Skill Changelog
> 框架规则库变更历史，对应 HyperAgents 的 evaluation history
> 每次 promote 操作自动追加条目，提供完整的规则溯源

---

## 使用说明

- 每条 promote 操作由 `skill-tracker/tracker.py promote` 自动写入
- 手动修改 SKILL.md 时，请手动追加对应条目
- 格式：`## <目标文件> — <日期>`

---

## 格式模板

```markdown
## .claude/skills/<skill-id>/SKILL.md — YYYY-MM-DD
- 来源候选：`<CANDIDATE_ID>`
- 规则：<proposed_rule 内容>
- 验证项目：<项目1>, <项目2>
- 类型：<candidate_type>
- 审核：人工批准
- 效果追踪：待验证（在 <下一个项目> 中观察是否减少对应失败）
```

---

## 变更记录

<!-- promote 操作自动追加到此处 -->

## .claude/skills/memory-update/SKILL.md — 2026-05-14
- 来源候选：manual correction from agent_lab_space memory-root miswrite
- 规则：项目 memory/session 写入前必须先判定资产所属项目根；sibling 子仓库资产优先于当前激活 `PROJECT_PATH`，缺少 `memory/INDEX.md` 时创建最小索引，不得退回写入当前激活项目。
- 验证项目：agentplatform, agent_lab_space
- 类型：skill_rule + hook_guidance
- 审核：人工批准（用户要求“优化执行规则”）
- 效果追踪：待验证（观察后续 workspace sibling 任务是否仍发生 memory 混写）
