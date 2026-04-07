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
此经验是否适用于其他项目？
    │
    ├─ 仅适用于本项目技术栈/需求 → 写入 projects/<n>/memory/
    │
    ├─ 可能适用但未验证 → 写入 projects/<n>/memory/（标注待验证）
    │
    └─ 跨项目验证（≥3个项目）→ 升级写入 memory/（框架记忆）
```

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

格式：`projects/<n>/memory/P_<项目缩写>_<序号>.md`

```markdown
---
id: P_XXX_001
title: [一句话总结，即为规则]
severity: BUG_FIX | DESIGN | PATTERN
created: YYYY-MM-DD
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

在以下区域追加条目：
- Bug 经验表（遇到的 Bug）
- 设计决策表（架构选择原因）

### Step 5: 检查框架记忆升级条件 / 候选草稿

检查 memory/INDEX.md IMPORTANT 区：
- 是否有新的跨项目模式需要添加？
- 是否有旧条目已被证伪需要删除？
- CRITICAL 区是否超过 7 条需要合并？

若经验具有跨项目复用潜力但验证不足（<3 项目），则先写入 `memory/candidates/`，等待人工审核或后续项目验证。

---

## 精简原则
- 不写"我知道了"，写"下次遇到 XXX 场景做 YYY"
- 标题即规则，不需要展开就能行动
- 旧条目定期审查，无用的删除，不积累垃圾
