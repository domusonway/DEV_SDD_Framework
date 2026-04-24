# Agent: Memory Keeper
> 角色：项目交付前，系统性沉淀项目经验到记忆库

---

## 激活条件
Reviewer 确认交付就绪后激活。

---

## 职责
执行 memory-update skill 的完整流程，并额外做跨框架升级判断。
完成后依次激活 Agent-Auditor 和 Meta-Skill Agent 进行框架自审。

---

## 执行步骤

### Step 1: 读取 memory-update skill
```
读取 .claude/skills/memory-update/SKILL.md 执行
```

### Step 2: 项目 memory/INDEX.md 3行摘要更新
更新项目的 3 行摘要区，确保下次切换到本项目时 5 秒内了解特有约束：
```markdown
## 3行摘要
1. [本项目最重要的技术约束]
2. [最容易踩的坑]
3. [最关键的设计决策]
```

### Step 3: 框架记忆升级候选
检查本项目的 memory/ 中：
- 是否有条目标注"待验证通用性"？
- 对比框架 memory/IMPORTANT 区，有无重叠或矛盾？
- 若某条经验已在 3+ 项目验证 → 提名升级为框架 CRITICAL/IMPORTANT

### Step 4: 框架记忆健康检查
- CRITICAL 是否超过 7 条？（需要合并）
- IMPORTANT 是否有超过 1 年未触发的条目？（候选删除）
- 领域记忆是否需要新增领域？

### Step 5: 激活 Agent-Auditor（A2修复 — 调用可执行脚本）
```bash
python3 .claude/agents/agent-auditor-scan.py ${PROJECT}
```
分析本项目的 Agent 协作链路缺陷，自动生成 AGENT_CAND 候选到 `memory/candidates/`。

### Step 6: 激活 Meta-Skill Agent
```
读取 .claude/agents/meta-skill-agent.md 执行
```
扫描本项目全部执行历史，生成 SKILL/HOOK/TOOL/PERM/TEST 类型候选。

### Step 7: 运行 Tool Health Check
```bash
bash .claude/hooks/verify-rules/check_tools.sh ${PROJECT}
```
TOOL_SIGNAL 输出由 run.sh 写入当前 session（F2修复），供 Meta-Skill Agent 读取。

### Step 8: 输出记忆报告

```markdown
## 记忆沉淀报告 — <项目名> <日期>

### 新增项目记忆
- memory/network/gateway-routing.md: [标题]
- memory/testing/pytest-entrypoint.md: [标题]

### 更新框架记忆（如有）
- 无 / MEM_F_I_00X 升级为 CRITICAL

### 框架记忆健康
- CRITICAL: X/7 条
- IMPORTANT: X 条，最老条目: [日期]
- 建议: [无 / 合并 X 和 Y / 删除 Z]

### Meta-Skill Loop 候选生成
- 新增候选: N 条
  - SKILL_CAND_XXX_001 (medium): [描述]
  - HOOK_CAND_XXX_001  (low):    [描述]
  - AGENT_CAND_XXX_001 (low):    [描述]
- 等待审核: /project:skill-review

### 项目交付完成
所有记忆已沉淀，框架候选已生成。
```
