# HOOK: session-snapshot
> 触发时机：① 对话开始 ② 任意决策完成后 ③ 对话结束前

---

## 文件路径规则

```
projects/<PROJECT>/memory/sessions/YYYY-MM-DD_HH-MM.md
```

每次对话对应一个文件。同一天多次对话按时间戳区分。

---

## 触发一：对话开始（session-start）

**触发条件**：启动协议 Step 2.5 执行时。

**执行动作**：调用 write.py 创建 session 文件，写入：

```markdown
---
status: in-progress
session_id: YYYY-MM-DD_HH-MM
project: <PROJECT>
task: <用户描述的任务，若未知写"待明确">
---

[SESSION-START]
时间: HH:MM
加载记忆: <已加载的 MEM_ID 列表，无则写"仅 CRITICAL">
项目状态: <PLAN.md 当前进度，如"批次1/3，request_parser 待实现">
续接: <若有上次 in-progress 文件，写"续接 YYYY-MM-DD_HH-MM"，否则写"新会话">
[/SESSION-START]
```

---

## 触发二：决策检查点（checkpoint）

**触发条件**（满足任一即触发）：
- 任意模块完成 GREEN（所有测试通过）
- 做出接口或架构设计决策
- 解决了 RED > 1 次的 Bug
- 完成 SPEC.md 或 CONTEXT.md 的撰写

**执行动作**：调用 write.py 追加到当前 session 文件：

```markdown
[CHECKPOINT HH:MM]
事件: <触发事件描述>
决策/结果: <做了什么，或得出了什么结论>
遇到的问题: <有则记录，无则省略>
当前状态: <模块名 / 测试通过数 / PLAN.md 进度>
[/CHECKPOINT]
```

---

## 触发三：会话结束（session-end）

**触发条件**（满足任一即触发）：
- 用户消息包含：结束/收工/先到这/明天/下次/暂停/我去/睡了/下班
- 用户明确说"今天先这样"类似表达
- 对话已连续无新代码任务超过 10 轮

**执行动作**：追加到当前 session 文件并更新 status：

```markdown
[SESSION-END]
时间: HH:MM
完成了: <本次完成的具体内容，按模块列出>
未完成: <明确的中断点，"正在做 XXX 的第 N 步">
下次继续: <一句话，明确的下一个动作>
记忆候选: <值得写入 memory 的经验，无则写"无">
[/SESSION-END]

---
status: completed
```

若对话突然中断未触发 session-end，status 保持 in-progress，
下次启动时会被 Step 2.5 检测到并提示续接。

---

## 执行脚本

```bash
# 写入 session-start
python3 .claude/hooks/session-snapshot/write.py start "<task>"

# 追加 checkpoint
python3 .claude/hooks/session-snapshot/write.py checkpoint "<event>" "<result>" "<state>"

# 写入 session-end
python3 .claude/hooks/session-snapshot/write.py end "<completed>" "<interrupted>" "<next>"
```

---

## 不可跳过的原则

- 即使任务未完成，session-end 也必须输出
- checkpoint 不需要等任务完成，决策发生即记录
- 文件一旦创建不得修改已有内容，只能追加
