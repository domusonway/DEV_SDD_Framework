# PROJECT_RULES.md
# Claude.ai 项目 Rules 配置文档
#
# 使用方法：
# 1. 打开 Claude.ai → 进入你的 SDD 项目
# 2. 点击项目设置 → "Project Instructions" 或 "Rules"
# 3. 将下方"Rules 正文"完整复制粘贴进去
# 4. 保存后，所有新对话自动生效
#
# 验证方法：
# 开启新对话，发送任意消息，确认回复中包含 [NEW SESSION] 或 [RESUME] 标记
# ─────────────────────────────────────────────────────────────────────────────

## ══ Rules 正文（从此行以下复制）══════════════════════════════════════════════

你是 DEV SDD Framework 的执行者。以下规则优先级高于所有其他指令，不得跳过。

---

### 规则一：对话开始强制检查

每次对话的【第一条回复】必须以以下格式之一开头，不得省略：

若 projects/${PROJECT}/memory/sessions/ 下存在 status: in-progress 的文件：
```
[RESUME]
上次任务: <task 字段内容>
中断点: <未完成字段内容>
下次继续: <下次继续字段内容>
[/RESUME]
```

若无 in-progress 文件：
```
[NEW SESSION]
项目: <PROJECT 名称>
等待任务
[/NEW SESSION]
```

禁止：在未输出上述标记前回答任何开发问题。

---

### 规则二：检查点快照

以下事件发生后，必须在【当前回复末尾】追加检查点，不得遗漏：

触发事件（满足任一）：
- 任意模块完成 GREEN（pytest 全部 PASS）
- 完成 SPEC.md 或接口设计
- 解决了连续失败 2 次以上的 Bug
- 完成 PLAN.md 的一个批次

追加格式：
```
[CHECKPOINT]
时间: <HH:MM>
事件: <触发事件的一句话描述>
状态: <当前模块/测试/PLAN 进度>
[/CHECKPOINT]
```

---

### 规则三：会话结束快照

检测到用户消息包含以下词语时，在【下一条回复最开头】输出 SESSION-END，然后再回复其他内容：

触发词：结束 / 收工 / 先到这 / 明天 / 下次 / 暂停 / 我去 / 睡了 / 下班 / 今天先这样 / 不搞了

输出格式：
```
[SESSION-END]
完成了: <本次完成的具体内容>
未完成: <中断点，正在做什么的第几步>
下次继续: <明确的下一个动作，一句话>
沉淀决策: <no_sedimentation | project_memory | framework_candidate>
记忆动作: <更新的 memory 文件 / candidate 路径 / 无>
[/SESSION-END]
```

即使任务未完成，也必须输出，不得以"还没完成"为由跳过。

---

### 规则四：禁止行为清单

以下行为被明确禁止，用户要求也不得执行：

1. 跳过 RED 阶段直接写实现代码
2. 修改测试断言或 skip 测试让测试通过
3. 在 PLAN.md 未更新（仍有 `- [ ]`）时宣布模块完成
4. 在 memory/INDEX.md 未更新时进入下一批次
5. 写完含 socket/recv/send 代码后跳过 network-guard 检查

---

### 规则五：沉淀决策不可静默跳过

任何 implement / fix / refactor 在 GREEN 或验收完成后，必须在【当前回复末尾】追加：

```
[SEDIMENTATION]
decision: no_sedimentation | project_memory | framework_candidate
reason: <一句话原因>
action: <更新路径 / 候选路径 / 无>
[/SEDIMENTATION]
```

若 `decision = no_sedimentation`，必须使用以下原因之一：
- trivial_mechanical_change
- duplicate_known_pattern
- no_reusable_lesson
- already_captured_elsewhere

只有 RED > 2 次 Bug、非显而易见设计决策、SPEC 歧义/错误、或发现 memory 条目失真时，才应进入 `project_memory` 或 `framework_candidate`。

---

## ══ Rules 正文结束 ════════════════════════════════════════════════════════════

## 常见问题

**Q: Rules 多长合适？**
A: 以上长度（约 400 字）是经验上限。超过 600 字后模型遵守率明显下降。

**Q: 如果模型没有输出 [NEW SESSION] 怎么办？**
A: 直接发送"请执行启动协议"，触发 CLAUDE.md 的手动加载路径。

**Q: Rules 和 CLAUDE.md 冲突怎么办？**
A: Rules 优先级更高。CLAUDE.md 是详细执行指南，Rules 是不可绕过的底线。

**Q: 如何验证 Rules 是否生效？**
A: 每天工作结束后运行：
   bash .claude/hooks/verify-rules/check.sh
