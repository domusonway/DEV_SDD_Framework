````markdown
# SKILL: context-probe
> 任务：读取用户任务描述，自动匹配并加载相关 memory 条目
> v3.0：新增 harness engineering 维度匹配

---

## 触发时机

启动协议 Step 2.5（读取 HANDOFF.json / session 续接检测）完成后，用户描述任务时立即执行。

---

## 执行步骤

### Step 1: 提取任务关键词

读取用户任务描述的前 300 字，识别以下维度：

| 维度 | 识别词 |
|------|--------|
| 网络编程 | socket / recv / send / TCP / UDP / 连接 / 服务器 |
| HTTP 协议 | HTTP / 响应 / 请求 / 状态码 / header / CGI |
| 跨语言重构 | C重构 / C迁移 / C语言 / port / 迁移 |
| TDD 问题 | 测试失败 / RED / 断言 / assert / 测试通过不了 |
| 多线程 | 线程 / threading / 并发 / 锁 / deadlock |
| 复杂度评估 | 新项目 / 开始开发 / 实现XXX系统 |
| 记忆沉淀 | 完成了 / 交付 / 全部通过 / 项目结束 |
| 长时任务（v3.0）| 多 session / 换个对话 / context / 续接 / H模式 / 批次 |
| 验证阶段（v3.0）| VALIDATE / 验收 / 检查实现 / 契约 / 接口一致性 |
| Context Budget（v3.0）| budget / 上下文 / session交接 / handoff |

### Step 2: 按规则自动加载

| 匹配维度 | 自动加载内容 |
|---------|------------|
| 网络编程 | MEM_F_C_004, MEM_F_C_005, MEM_F_I_001, MEM_F_I_002 |
| HTTP 协议 | memory/domains/http/INDEX.md（全量） |
| 跨语言重构 | MEM_F_I_004, MEM_F_I_005 |
| TDD 问题 | MEM_F_I_006, MEM_F_C_003 |
| 多线程 | MEM_F_I_007 |
| 复杂度评估 | .claude/skills/complexity-assess/SKILL.md |
| 记忆沉淀 | .claude/skills/memory-update/SKILL.md |
| 长时任务（v3.0）| MEM_F_I_008, MEM_F_I_011，.claude/skills/sub-agent-isolation/SKILL.md |
| 验证阶段（v3.0）| MEM_F_I_009，.claude/skills/observe-verify/SKILL.md |
| Context Budget（v3.0）| MEM_F_I_008, MEM_F_I_010，.claude/hooks/context-budget/HOOK.md |
| 无明确匹配 | 仅 CRITICAL 内联（已足够） |

**加载上限：单次最多加载 4 条 IMPORTANT 记忆**
超出时优先加载与任务最直接相关的条目。

### Step 3: 输出加载确认

格式固定，必须输出：

```
[CONTEXT-PROBE]
匹配维度: <识别出的维度，多个用逗号分隔>
自动加载: <MEM_ID 列表或 SKILL 路径，或"仅 CRITICAL">
跳过加载: <因上限截断的条目，无则省略此行>
[/CONTEXT-PROBE]
```

---

## 与启动协议的衔接

context-probe 的输出写入当前 session 文件的 `加载记忆` 字段。

HANDOFF.json 存在时，优先根据 `context_notes` 字段补充加载。

---

## 局限性说明

context-probe 是关键词匹配，有误判可能。
**遇到误判时**：直接告诉 Claude "加载 MEM_F_XXX"，手动覆盖自动加载结果。

---

## 维护说明

当 memory/INDEX.md 新增 IMPORTANT 条目时，需同步更新本文件的匹配规则表。
v3.0 已新增：长时任务 / 验证阶段 / Context Budget 三个维度。

````

