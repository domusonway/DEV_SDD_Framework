# SKILL: memory-update
> 任务：项目完成后沉淀有价值的记忆，保持记忆库精简高效

---

## 触发时机
任何 implement / fix / refactor 在 GREEN + VALIDATE 通过后立即执行；项目交付前必须再次复核。

---

## 记忆沉淀流程

### Step 1: 收集候选记忆
回顾本项目中：
- 遇到过哪些 Bug？（特别是 RED > 2 次的）
- 有哪些设计决策值得记录？
- 有哪些 SPEC 不清晰导致返工的地方？
- 有哪些工具/方法特别有效？

### Step 2: 判断记忆归属

```
先确定资产所属项目根 ASSET_PROJECT_ROOT：
    │
    ├─ 本轮主要修改/验证的文件在当前 PROJECT_PATH 下 → ASSET_PROJECT_ROOT = 当前 PROJECT_PATH
    ├─ 本轮主要修改/验证的文件在 sibling 子仓库下 → ASSET_PROJECT_ROOT = 该 sibling 子仓库根
    └─ 只涉及框架自身或跨项目候选 → 不写项目 memory，走 candidates 或 framework memory

此经验是否适用于其他项目？
    │
    ├─ 仅适用于资产所属项目技术栈/需求 → 写入 <ASSET_PROJECT_ROOT>/memory/
    │
    ├─ 可能适用但未验证 → 写入 <ASSET_PROJECT_ROOT>/memory/（标注待验证）
    │
    └─ 跨项目验证（≥3个项目）→ 升级写入 memory/（框架记忆）
```

`PROJECT_PATH` 是默认上下文，不是强制写入根。若任务主体属于 sibling 子仓库（例如 `agent_lab_space`），必须写入该子仓库的 `memory/`。若目标子仓库尚无 `memory/INDEX.md`，先创建最小索引；不得因为索引缺失而写入当前激活项目或 workspace 根。

### Step 2.5: 做出 Sedimentation Decision（不可跳过）

每次闭环完成后，必须显式输出：

```markdown
[SEDIMENTATION]
decision: no_sedimentation | project_memory | framework_candidate
reason: <一句话原因>
action: <写入的 memory 文件路径 / candidate 路径 / 无>
[/SEDIMENTATION]
```

判定规则：
- `no_sedimentation`：纯机械改动、已有 memory 完全覆盖、或无可复用经验
- `project_memory`：经验对当前项目稳定适用，但尚不足以提升为框架规则
- `framework_candidate`：经验具有跨项目复用潜力，但尚未满足正式 promote 条件

若选择 `no_sedimentation`，推荐使用固定原因：
- `trivial_mechanical_change`
- `duplicate_known_pattern`
- `no_reusable_lesson`
- `already_captured_elsewhere`

### Step 3: 写项目记忆文件

格式：`<ASSET_PROJECT_ROOT>/memory/<domain>/<topic>.md`。若配置 `PROJECT_PATH`，它只在资产属于当前激活项目时作为默认 `<ASSET_PROJECT_ROOT>`；workspace 根、`projects/<PROJECT>` fallback、以及 sibling 项目 memory 都不得混写目标子项目记忆。

示例：
- `projects/HarnessEvaluationFramework/memory/network/gateway-routing.md`
- `projects/HarnessEvaluationFramework/memory/testing/pytest-entrypoint.md`
- `projects/agentplatform_workspace/agent_lab_space/memory/validation/sampling-stage-gate.md`（lab-only 规则，不得写入 sibling `agentplatform/memory/`）

```markdown
---
id: MEM_<DOMAIN>_<TOPIC>
title: [一句话总结，即为规则]
severity: BUG_FIX | DESIGN | PATTERN
domain: network | testing | data | workflow | runtime
created_at: YYYY-MM-DD HH:MM
updated_at: YYYY-MM-DD HH:MM
---

## 规则
[清晰的一句话]

## 背景
[为什么会遇到这个问题]

## 反例 → 后果
[错误做法及其后果]

## 正例
[正确做法，含代码示例]
```

### Step 4: 更新项目 memory/INDEX.md

更新 `<ASSET_PROJECT_ROOT>/memory/INDEX.md`。若不存在，先创建最小索引，然后在以下区域追加条目：
- Bug 经验表（遇到的 Bug）
- 设计决策表（架构选择原因）

### Step 5: 检查框架记忆升级条件 / 候选草稿

检查 memory/INDEX.md IMPORTANT 区：
- 是否有新的跨项目模式需要添加？
- 是否有旧条目已被证伪需要删除？
- CRITICAL 区是否超过 7 条需要合并？

若经验具有跨项目复用潜力但验证不足（<3 项目），则先写入 `memory/candidates/`，等待人工审核或后续项目验证。

### Step 6: 记录记忆使用效果（新增）

当某条项目/领域/框架记忆在本轮任务中被加载或应用时，使用 memory-usage 工具记录效果：

```bash
python3 .claude/tools/memory-usage/run.py record <MEMORY_ID> \
  --project <PROJECT> \
  --source framework|project|domain|candidate \
  --task "<任务摘要>" \
  --outcome loaded|applied|helped|neutral|misled|stale \
  --note "<一句话证据>"
```

效果统计：

```bash
python3 .claude/tools/memory-usage/run.py summary --project <PROJECT> --json
```

剪枝建议与废弃记录：

```bash
python3 .claude/tools/memory-usage/run.py prune --project <PROJECT> --json
python3 .claude/tools/memory-usage/run.py deprecate <MEMORY_ID> --project <PROJECT> --reason "<原因>" --replacement "<替代记忆，可选>"
```

用途：长期判断哪些记忆真正帮助开发，哪些造成误导或过期，供后续 pruning / deprecate 使用。

---

## 精简原则
- 不写"我知道了"，写"下次遇到 XXX 场景做 YYY"
- 标题即规则，不需要展开就能行动
- 旧条目定期审查，无用的删除，不积累垃圾
