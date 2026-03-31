# Candidate Schema
# 所有观察器生成的候选 YAML 格式规范
# 路径：memory/candidates/SCHEMA.md

---

## candidate_type 类型表

| 值 | 说明 | 提升目标 | 提升方式 |
|----|------|---------|---------|
| `skill_rule` | SKILL.md 中新增或修改规则 | `.claude/skills/*/SKILL.md` | 追加到文件末尾 |
| `hook_trigger` | Hook 触发条件扩展 | `.claude/hooks/*/HOOK.md` | 追加到触发条件章节 |
| `hook_check` | Hook 检查清单新增项 | `.claude/hooks/*/HOOK.md` 和 `check.py` | 追加 |
| `agent_constraint` | Agent 角色约束补充 | `.claude/agents/*.md` | 追加到执行步骤 |
| `agent_role_gap` | 需要新增 Agent 角色 | `.claude/agents/<new>.md` | 创建新文件 |
| `planner_risk_dimension_missing` | Planner 缺少风险评估维度 | `.claude/agents/planner.md` | 追加风险维度 |
| `tool_subcommand` | 现有工具新增子命令 | `.claude/tools/*/*.py` | 追加函数 |
| `tool_new` | 需要新增工具 | `.claude/tools/<new>/` | 创建新文件 |
| `permission_relax` | 将 deny 移至 ask | `.claude/settings.local.json` | 人工编辑 |
| `permission_tighten` | 收紧 allow 范围 | `.claude/settings.local.json` | 人工编辑 |
| `test_stub` | 缺失的测试桩 | `skill-tests/cases/test_*.py` | test-sync 自动追加 |
| `command_missing` | 缺失的 command | `.claude/commands/*.md` | 创建新文件 |

---

## 字段规范

```yaml
# 必填字段
id: <TYPE>_CAND_<PROJECT-SLUG>_<序号3位>

candidate_type: <见上方类型表>

source_observer: meta-skill-agent | hook-observer | agent-auditor
                 | check_tools | permission-auditor | test-sync

source_project: <项目名（完整）>

observed_evidence: |
  <引用具体证据：session 文件名、关键内容摘要，≤400字>

observed_pattern_key: <去重键，格式 "observer_type:pattern:target">

proposed_rule: "<一句话规则，即为规则标题>"

target_file: <相对于框架根目录的路径>

proposed_diff: |
  <具体修改内容，说明在哪里添加什么>

confidence: low | medium | high
  # low = 1个项目，medium = 2个项目，high = ≥3个项目

validated_projects:
  - <项目名1>
  - <项目名2>

status: pending_review | approved | rejected | promoted

# ── auto_attach 字段（TASK-ANN-01 新增）──────────────────────────────────────
auto_attach: false
  # 含义：是否在 context-probe 领域匹配时，将 proposed_diff 作为临时规则注入上下文
  # 默认：false
  # 启用条件：confidence >= medium 且 status == pending_review
  # 人工设置：tracker.py attach <id>  /  tracker.py detach <id>
  # 效果：Agent 在本次会话中将 [TEMP_RULE from <id>] 视为与正式规则同等效力的约束
  # 安全边界：auto_attach 不触发任何文件写入，只影响 context-probe 的输出内容

# ── auto_attach 质量追踪字段（由 memory-keeper Step 5.5 维护）─────────────
auto_attach_triggered_projects: []
  # 记录哪些项目实际触发了此候选的临时规则
  # 格式：["project_a", "project_b"]

auto_attach_issues: []
  # 记录临时规则触发后发现的问题（若有）
  # 格式：["project_a: 描述问题"]

created: YYYY-MM-DD

# 可选字段
domain: <领域标签，用于 context-probe 匹配>
secondary_target: <主目标之外还需修改的文件>
failure_count: <在 source_project 中出现的次数>
promoted_at: YYYY-MM-DD
reject_reason: <拒绝原因>
```

---

## auto_attach 生命周期

```
[候选生成] auto_attach: false（默认）
    ↓ confidence 达到 medium（≥2项目验证）
[人工评估] tracker.py attach <id> → auto_attach: true
    ↓ 新项目启动，context-probe 领域匹配
[临时激活] [TEMP_RULE from <id>] 注入上下文，Agent 遵守临时规则
    ↓ 项目交付，memory-keeper Step 5.5 审查
[质量更新] 追加 auto_attach_triggered_projects
    ├─ 无副作用 → validated_projects 增加，confidence 可能升为 high
    │   ↓ confidence = high → /project:skill-review 正式 promote
    └─ 有问题 → auto_attach: false，追加 auto_attach_issues
```

---

## 置信度升级规则

| validated_projects 数量 | confidence |
|------------------------|-----------|
| 1 | low |
| 2 | medium |
| ≥3 | high |

执行 `skill-tracker validate <id> --project <p>` 时自动升级。

---

## 文件命名规则（A1修复）

```
<TYPE>_CAND_<PROJECT-SLUG>_<序号>.yaml

TYPE 前缀：
  SKILL  → skill_rule
  HOOK   → hook_trigger, hook_check
  AGENT  → agent_constraint, agent_role_gap, planner_risk_dimension_missing
  TOOL   → tool_subcommand, tool_new
  PERM   → permission_relax, permission_tighten
  TEST   → test_stub
  CMD    → command_missing

PROJECT-SLUG：
  规则：re.sub(r"[^a-zA-Z0-9]", "-", project_name).upper()[:20]

序号：3位数字，001 起，在同类型+同项目中递增
```
