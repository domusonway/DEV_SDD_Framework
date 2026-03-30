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
