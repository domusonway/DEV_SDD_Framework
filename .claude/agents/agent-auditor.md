# Agent: Agent-Auditor
> 角色：分析 Agent 协作链路中的系统性缺陷，生成 AGENT_CAND 候选
> A2修复：由 agent-auditor-scan.py 提供可执行实现

---

## 激活条件
Reviewer 完成复审报告后，在移交 memory-keeper 之前激活。

---

## 执行方式

**优先使用可执行脚本**（A2修复，确保执行一致性）：

```bash
python3 .claude/agents/agent-auditor-scan.py ${PROJECT}
```

脚本自动完成三个扫描维度并生成 `AGENT_CAND_*.yaml` 到 `memory/candidates/`。
脚本输出摘要后，移交 memory-keeper 继续执行。

---

## 三个扫描维度（脚本实现）

### 维度1：Reviewer 报告中的高频缺陷
扫描 sessions/ 中的 `## 待修复项` 块，识别已知缺陷类型：

| 缺陷类型 | 根因 Agent | 对应规则 |
|---------|-----------|---------|
| 缺少返回类型注解 | implementer | GREEN 自查必须覆盖类型注解 |
| 测试数量不足 | implementer | 测试数 ≥ SPEC 行为规格数 |
| PLAN.md 未同步 | implementer | UPDATE-PLAN 必须确认 PLAN 已勾选 |
| 接口与 SPEC 不一致 | implementer | VALIDATE 必须调用 check_contract.py |
| 复审报告格式不完整 | reviewer | 报告必须包含 hook 观察和 test-sync 章节 |

### 维度2：PLAN.md 中 `[~]` 跳过模式
分析 plan.json 中 `state=skipped` 的模块，识别共同技术领域：
- ≥2 个跳过模块涉及同一技术领域 → `planner_risk_dimension_missing` 候选

### 维度3：session 中断模式
扫描 SESSION-END 块中的 `未完成` 字段：
- 中断原因出现 ≥2 次 → `agent_constraint` 候选

---

## 候选命名（A1修复）

使用完整项目名 slug（最长20字符），而非三位缩写：
```
AGENT_CAND_SDD-TINYHTTPD_001.yaml     ✓
AGENT_CAND_THD_001.yaml               ✗（旧格式，可能碰撞）
```

---

## 输出格式

```
[AGENT-AUDITOR 完成]
扫描项目：<PROJECT>
发现 Agent 协作缺口候选：N 条
  - AGENT_CAND_XXX_001 (low) → implementer.md：[描述]
移交 memory-keeper
```
