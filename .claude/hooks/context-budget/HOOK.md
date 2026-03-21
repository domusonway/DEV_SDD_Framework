# HOOK: context-budget
> 触发时机：每完成一个模块 GREEN，或 session 内消息轮次超过阈值时检查

---

## 为什么需要 Context Budget 管理

Context rot 是长时任务最大的隐性杀手。Chroma 研究证明：随上下文增长，模型在**所有任务**上的表现均匀下降——不只是忘记后面的指令，而是对整个上下文的推理质量下降。

**你的 context budget 分配：**

| 类型 | 预估 token 消耗 | 备注 |
|------|---------------|------|
| CLAUDE.md + 启动协议 | ~2000 | 每次 session 固定消耗 |
| 每个 SKILL.md 加载 | ~500-1500 | 按需加载 |
| 每轮代码交互 | ~1000-3000 | 含工具调用输出 |
| pytest 输出 | ~500-2000 | 可能很长 |
| 安全阈值（估算）| ~60,000 | 超过开始退化 |

---

## 检查触发规则

以下任一条件满足，立即执行预算检查：

1. **模块粒度**：完成任意模块 GREEN（tdd-cycle UPDATE-PLAN 阶段后）
2. **轮次粒度**：当前 session 已进行 **15 轮以上**交互
3. **手动触发**：用户说"检查 context"或发现模型开始重复/混乱

---

## 检查清单

```
□ 本 session 已完成模块数: ___
□ 估算剩余 budget（主观感知）: 充裕 / 紧张 / 危险
□ 下一批次模块复杂度: L / M / H
□ 当前有未记录到文件的中间结果: 是 / 否
```

---

## 决策树

```
剩余 budget 是否足以完成下一个模块？
    │
    ├─ 是（充裕）→ 继续，在下一模块完成后再次检查
    │
    ├─ 紧张（估计刚好够）→ 执行「轻量收尾协议」后继续
    │
    └─ 危险（明显不够）→ 执行「强制 Session 交接」
```

---

## 轻量收尾协议（budget 紧张时）

在当前模块完成后，下一模块开始前：

1. 确认 PLAN.md 已更新（本模块 `[x]`）
2. 确认 memory/INDEX.md 接口快照已更新（`🟢`）
3. 执行 session-snapshot checkpoint
4. **清理上下文**：告知用户"建议在此处开启新对话续接，以保持模型推理质量"

---

## 强制 Session 交接协议（budget 危险时）

**立即停止当前模块实现**，执行交接：

### Step 1: 写入 handoff 文件

在项目根目录写入 `HANDOFF.json`：

```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SS",
  "session_ended_reason": "context_budget",
  "project": "<PROJECT>",
  "last_completed_module": "<module>",
  "current_state": "GREEN/RED/REFACTOR",
  "next_action": "<明确的下一步，一句话>",
  "blockers": [],
  "plan_progress": {
    "completed": ["<module_a>", "<module_b>"],
    "in_progress": [],
    "pending": ["<module_c>", "<module_d>"]
  },
  "interface_snapshots": {
    "<module>": {"status": "🟢", "key_interface": "<函数签名>"}
  },
  "context_notes": "<任何对下一个 session 重要的上下文>"
}
```

### Step 2: 提交 git checkpoint

```bash
git add -A
git commit -m "checkpoint: session handoff at <module> — <next_action>"
```

### Step 3: 触发 session-end

执行 `.claude/hooks/session-snapshot/write.py end` 写入 SESSION-END。

### Step 4: 告知用户

输出：
```
[CONTEXT-BUDGET] ⚠️ Budget 危险，已执行 session 交接
HANDOFF.json 已写入，git checkpoint 已提交
请开启新对话，框架会自动续接
下一步: <next_action>
```

---

## 新 Session 启动时的交接接收

启动协议 Step 2.5 中，若存在 `HANDOFF.json`：

1. 读取 HANDOFF.json
2. 优先显示 `next_action`，覆盖 session-snapshot 的 in-progress 提示
3. 验证 git 状态与 HANDOFF 一致（`git log --oneline -3`）
4. 删除 HANDOFF.json（已读取，避免下次误触发）

---

## 关键原则

- **宁可多交接，不要 context rot**：在 budget 紧张时提前交接比继续撑着质量更高
- **HANDOFF.json 用 JSON 不用 markdown**：模型不会随意覆盖 JSON（Anthropic 实践验证）
- **交接是里程碑，不是中断**：每次交接前必须确保状态干净（GREEN + 文档同步）
