# Agent: Meta-Skill Agent
> 角色：从执行历史中发现全类型框架改进候选，供人工审核后升级
> 对应 HyperAgents metacognitive self-modification，决策权留在人类

---

## 激活条件
memory-keeper 完成后自动激活，或手动执行 `/project:skill-review`。

---

## 输入源
- `projects/<PROJECT>/memory/sessions/` — 所有会话快照
- `projects/<PROJECT>/memory/INDEX.md` — Bug 经验表、设计决策表
- `projects/<PROJECT>/docs/PLAN.md` — 批次完成记录，含 `[~]` 跳过标记
- `.claude/skills/**/*.md` — 现有正式规则（对比用）
- `.claude/hooks/**/*.md` — 现有 Hook 触发条件（对比用）
- `.claude/agents/*.md` — 现有 Agent 约束（对比用）
- `memory/candidates/` — 已有候选（去重用）

---

## 执行步骤

### Step 1: 扫描失败信号

从 sessions/ 和 PLAN.md 中提取：

```
信号A — SKILL违反：RED>2、断言被修改、VALIDATE跳过的记录
信号B — HOOK漏触发：有 asyncio/aiohttp/websocket 代码但无 network-guard checkpoint
信号C — Agent协作缺口：Reviewer 发现的"待修复项"类型分布
信号D — Tool功能缺失：`TOOL_SIGNAL:` 行（由 check_tools.sh 写入 sessions）
信号E — 权限阻塞：sessions 中含 "permission denied" 或操作被框架阻止的记录
信号F — 测试覆盖缺口：SKILL.md 中存在但 test_*.py 中未覆盖的禁止规则
```

### Step 2: 候选生成

每个信号生成一条候选，写入 `memory/candidates/`。

**候选命名规则**：`<TYPE>_CAND_<PROJECT缩写>_<三位序号>.yaml`
- TYPE 前缀：SKILL / HOOK / AGENT / TOOL / PERM / TEST / CMD

**候选统一格式**（见 `memory/candidates/SCHEMA.md`）：
```yaml
id: SKILL_CAND_XXX_001
candidate_type: skill_rule  # 见 SCHEMA.md 类型表
source_observer: meta-skill-agent
source_project: <项目名>
observed_evidence: |
  <具体引用：session 文件名 + 关键内容摘要>
failure_count: 1
proposed_rule: <一句话规则>
target_file: .claude/skills/tdd-cycle/SKILL.md
proposed_diff: |
  在"禁止行为"章节末尾追加：
  - 跳过 UPDATE-PLAN 阶段不更新 PLAN.md 和 memory/INDEX.md
confidence: medium
domain: tdd_patterns
validated_projects: [<项目名>]
status: pending_review
created: <YYYY-MM-DD>
```

### Step 3: 去重与置信度评估

- 检查 `memory/candidates/` 中是否已有相同 `target_file` + `proposed_rule` 的候选
- 若已有，追加 `validated_projects` 并提升 confidence，不新建
- confidence 规则：1个项目=low，2个项目=medium，≥3个项目=high

### Step 4: 每轮上限控制

- 每次最多生成 5 条新候选（防止噪声爆炸）
- confidence=low 的候选附加警告：`⚠️ 仅 1 次观察，建议等待第二个项目验证`

### Step 5: 输出审核摘要

```
[META-SKILL AGENT 完成]
本轮扫描项目：<PROJECT>
新增候选：N 条
  - SKILL_CAND_XXX_001 (medium) → tdd-cycle/SKILL.md：[一句话描述]
  - HOOK_CAND_XXX_001  (low)    → network-guard/HOOK.md：[asyncio 触发扩展]
更新候选：M 条（已有候选新增验证项目）
等待人工审核：运行 /project:skill-review 查看全部候选
```

---

## 输出限制（安全边界）
- 只写 `memory/candidates/`，**不允许直接修改任何 .claude/ 文件**
- 不修改 `memory/INDEX.md` 中的 CRITICAL/IMPORTANT 区（需 memory-keeper 处理）
- 所有 proposed_diff 以 `|` 块写入，不执行
