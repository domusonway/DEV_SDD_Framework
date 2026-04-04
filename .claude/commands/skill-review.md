# /project:skill-review — 审核并提升框架改进候选

## 用法
```
/project:skill-review
/project:skill-review --type hook_trigger   # 只审核特定类型
/project:skill-review --min-validated 2     # 只审核 ≥2 项目验证的候选
```

## 执行步骤

### Step 1: 显示待审核候选
```bash
python3 .claude/tools/skill-tracker/tracker.py candidates --status pending_review
```

### Step 2: 逐条审核
对每条候选，Claude 展示：
- 候选 ID 和类型
- 触发的观察信号（原始 session 片段）
- 建议的 proposed_diff 内容
- 影响的目标文件

然后询问：`[A]pprove / [R]eject / [S]kip / [E]dit`

### Step 3: 批准后自动 promote
```bash
# 批准
python3 .claude/tools/skill-tracker/tracker.py approve <id>

# 执行 promote（写入目标文件 + 触发 test-sync）
python3 .claude/tools/skill-tracker/tracker.py promote <id>
```

### Step 4: 输出 promote 报告
```
[SKILL-REVIEW 完成]
本轮审核：N 条
  已批准并 promote：X 条
    - SKILL_CAND_XXX_001 → tdd-cycle/SKILL.md（已追加规则）
    - HOOK_CAND_XXX_001  → network-guard/HOOK.md（已追加触发条件）
  已拒绝：Y 条
  已跳过：Z 条
测试同步：test-sync 已自动运行
```

## 审核原则

### 批准标准
- confidence=high（≥3 项目验证）→ 通常直接批准
- confidence=medium（2 项目）→ 审查 proposed_diff 是否合理
- confidence=low（1 项目）→ 需要明确判断，通常选择 Skip 等待更多验证

### 拒绝标准 (reject)
- proposed_diff 会破坏现有正确行为
- 观察信号是偶然情况，非系统性问题
- 与已有规则重复

### 权限类候选特殊处理
- `permission_relax`：拒绝率应高，每条都需要充分理由
- `permission_tighten`：通常批准，降低风险

## 注意事项
- promote 后修改会自动追加到目标文件末尾，**不修改现有内容**
- 若 proposed_diff 需要插入特定位置而非追加，人工编辑后执行：
  `python3 .claude/tools/skill-tracker/tracker.py promote <id> --confirm`
- 权限类候选（PERM_CAND）promote 只输出提示，不自动修改 settings.local.json
