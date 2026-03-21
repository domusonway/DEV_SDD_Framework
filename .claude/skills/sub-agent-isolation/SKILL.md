````markdown
# SKILL: sub-agent-isolation
> 任务：在 H 模式长时任务中，通过文件系统作为隔离边界，实现 Context Firewall

---

## 为什么需要 Sub-Agent 隔离

在同一个对话里运行 Planner → Implementer → Reviewer，意味着：
- Planner 读取的所有 SPEC 文件在 context 里
- Implementer 写的所有代码在 context 里
- Reviewer 读取的所有测试在 context 里

到项目交付时，context window 已经充满噪声，推理质量显著下降。

**Context Firewall 原则：**
> 每个 agent 只看自己需要的信息。父 agent 只看子 agent 的最终输出，不看中间过程。

---

## H 模式的正确工作流

### 阶段划分（每阶段 = 一个独立对话）

```
对话 1: Initializer（初始化环境）
    ↓ 产出: HANDOFF.json + git init + plan.json + SPEC 文件
对话 2+: Implementer（实现批次，每批次一个对话）
    ↓ 产出: 代码 + 测试 + HANDOFF.json
最后 1 个对话: Reviewer（复审 + 交付）
    ↓ 产出: 复审报告 + memory 沉淀
```

### 文件系统作为隔离边界

每个 agent 通过以下文件交换状态，**不依赖对话历史**：

| 文件 | 写入方 | 读取方 | 说明 |
|------|--------|--------|------|
| `projects/<n>/HANDOFF.json` | 任意 agent | 下一个 agent | 交接状态 |
| `projects/<n>/docs/plan.json` | Planner | Implementer | 实现计划 |
| `projects/<n>/memory/INDEX.md` | Implementer | Reviewer | 接口快照 |
| `projects/<n>/memory/sessions/` | 所有 agent | 下一个 agent | 历史记录 |
| `git log` | Implementer | 所有 | 代码历史 |

---

## Initializer 对话的任务

**触发条件：** 新项目首次启动（复杂度 H 模式）

**Initializer 必须产出：**

```bash
# 1. 初始化 git
git init && git add -A && git commit -m "init: project scaffold"

# 2. 生成详细的 plan.json（包含所有模块+依赖关系）
python3 .claude/tools/plan-tracker/tracker.py render

# 3. 写入初始 HANDOFF.json（第一个 Implementer 对话的起点）
python3 .claude/hooks/context-budget/handoff.py write \
    --module "init" \
    --state GREEN \
    --next "实现批次1: [模块列表]，从 plan.json 批次1开始" \
    --reason "initializer_complete"

# 4. 写 init.sh（让每个新 session 快速验证环境）
```

**init.sh 内容（Initializer 生成）：**

```bash
#!/bin/bash
# 每个新 session 开始时运行，验证环境正常
set -e
echo "=== 环境验证 ==="
python3 -m pytest tests/ -v --tb=short -q 2>&1 | tail -5
echo "=== 当前进度 ==="
python3 .claude/tools/plan-tracker/tracker.py status
echo "=== 最近提交 ==="
git log --oneline -5
```

---

## Implementer 对话的标准开场

每个 Implementer 对话启动时，**启动协议 Step 2.5** 会自动读取 HANDOFF.json。

**如果没有自动读取，手动执行：**

```bash
# 1. 读取交接信息
python3 .claude/hooks/context-budget/handoff.py read

# 2. 验证环境
bash init.sh

# 3. 确认下一步任务
python3 .claude/tools/plan-tracker/tracker.py status
```

---

## Implementer 对话的标准结束

每个 Implementer 对话结束时（完成一个批次或 context budget 危险时）：

```bash
# 1. 提交进度
git add -A && git commit -m "feat: complete <module> — <brief_description>"

# 2. 写交接
python3 .claude/hooks/context-budget/handoff.py write \
    --module "<last_completed>" \
    --state GREEN \
    --next "<next_batch_description>"

# 3. 触发 session-end
python3 .claude/hooks/session-snapshot/write.py end \
    "<completed>" "<interrupted>" "<next_step>"
```

---

## 对话间的上下文传递规范

**父 agent 只需要知道的信息（高度压缩）：**

```
✅ plan.json 当前状态（通过 tracker.py status）
✅ HANDOFF.json 的 next_action
✅ git log --oneline -10
✅ memory/INDEX.md 接口快照
```

**父 agent 不需要的信息（不要读入 context）：**

```
❌ 所有中间 pytest 输出
❌ 所有读取过的实现代码细节
❌ 所有 session 快照的完整内容
```

---

## 关键原则

- **每个对话独立**：不依赖前一个对话的 context，只依赖文件
- **状态必须在文件里**：任何重要的中间状态，立即写文件（不只在 context 里）
- **git 是最可靠的状态存储**：每个里程碑提交，让下一个 agent 可以快速 `git log`
- **压缩输出**：子 agent 的结果高度压缩后传递，不要把中间过程的噪声带给父 agent

````

