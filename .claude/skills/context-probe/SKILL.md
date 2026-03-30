````markdown
# SKILL: context-probe
> 任务：读取用户任务描述，自动匹配并加载相关 memory 条目
> v3.2：候选预警改为实际可执行路径（M3修复）

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
| 异步网络 | asyncio / aiohttp / websocket / StreamReader / httpx |
| HTTP 协议 | HTTP / 响应 / 请求 / 状态码 / header / CGI |
| 跨语言重构 | C重构 / C迁移 / C语言 / port / 迁移 |
| TDD 问题 | 测试失败 / RED / 断言 / assert / 测试通过不了 |
| 多线程 | 线程 / threading / 并发 / 锁 / deadlock |
| 类型安全 | bytes / str / int / dtype / 类型错误 / TypeError |
| 复杂度评估 | 新项目 / 开始开发 / 实现XXX系统 |
| 记忆沉淀 | 完成了 / 交付 / 全部通过 / 项目结束 |
| 长时任务 | 多 session / 换个对话 / context / 续接 / H模式 / 批次 |
| 验证阶段 | VALIDATE / 验收 / 检查实现 / 契约 / 接口一致性 |
| Context Budget | budget / 上下文 / session交接 / handoff |
| 框架改进 | candidate / 候选 / skill-review / 规则提升 |

### Step 2: 按规则自动加载

| 匹配维度 | 自动加载内容 |
|---------|------------|
| 网络编程 | MEM_F_C_004, MEM_F_C_005, MEM_F_I_001, MEM_F_I_002 |
| 异步网络 | memory/domains/concurrency/INDEX.md + MEM_F_C_004 |
| HTTP 协议 | memory/domains/http/INDEX.md（全量） |
| 跨语言重构 | MEM_F_I_004, MEM_F_I_005 |
| TDD 问题 | MEM_F_I_006, MEM_F_C_003, memory/domains/tdd_patterns/INDEX.md |
| 类型安全 | MEM_F_C_002, memory/domains/type_safety/INDEX.md |
| 多线程 | MEM_F_I_007, memory/domains/concurrency/INDEX.md |
| 复杂度评估 | .claude/skills/complexity-assess/SKILL.md |
| 记忆沉淀 | .claude/skills/memory-update/SKILL.md |
| 长时任务 | MEM_F_I_008, .claude/skills/sub-agent-isolation/SKILL.md |
| 验证阶段 | MEM_F_I_009, .claude/skills/observe-verify/SKILL.md |
| Context Budget | MEM_F_I_010, .claude/hooks/context-budget/HOOK.md |
| 框架改进 | .claude/tools/skill-tracker/tracker.py（帮助） |
| 无明确匹配 | 仅 CRITICAL 内联（已足够） |

**加载上限：单次最多加载 4 条 IMPORTANT 记忆**

### Step 3: 候选预警（M3修复 — 实际可执行路径）

**执行方式**：在 Step 2 完成后，运行以下命令读取候选状态：

```bash
python3 .claude/tools/skill-tracker/tracker.py candidates \
    --status pending_review \
    --min-validated 2 \
    2>/dev/null | head -30
```

**筛选条件**：只展示 `validated_projects ≥ 2` 且 `domain` 与当前任务匹配的候选。

domain 与任务维度的对应关系：
| 当前任务维度 | 匹配的 domain |
|------------|--------------|
| 网络编程 / 异步网络 | network_code |
| TDD 问题 | tdd_patterns |
| 类型安全 | type_safety |
| 多线程 | concurrency |
| HTTP 协议 | http |

**预警输出格式**（有匹配候选时追加到 context-probe 输出末尾）：

```
[CANDIDATE PRE-WARN]
以下候选已在 ≥2 个项目验证，尚待正式提升，请主动注意：
- HOOK_CAND_SDD-TINYHTTPD-001 (medium, 2项目)：
  "network-guard 触发条件应扩展覆盖 asyncio 代码"
  → 本项目含异步网络代码时，请手动执行 network-guard 检查
[/CANDIDATE PRE-WARN]
```

**每次最多显示 3 条**，优先显示 confidence=high。
若 `skill-tracker` 命令不存在或 candidates/ 为空，静默跳过，不报错。

### Step 4: 输出加载确认

格式固定，必须输出：

```
[CONTEXT-PROBE]
匹配维度: <识别出的维度，多个用逗号分隔>
自动加载: <MEM_ID 列表或 SKILL 路径，或"仅 CRITICAL">
跳过加载: <因上限截断的条目，无则省略此行>
候选预警: <N 条 / 无>
[/CONTEXT-PROBE]
```

---

## 与启动协议的衔接

context-probe 的输出写入当前 session 文件的 `加载记忆` 字段。
HANDOFF.json 存在时，优先根据 `context_notes` 字段补充加载。

---

## 局限性说明

context-probe 是关键词匹配，有误判可能。
遇到误判时：直接告诉 Claude "加载 MEM_F_XXX"，手动覆盖自动加载结果。
候选预警中 confidence=low 的条目不显示（避免单次观察造成噪声）。

---

## 维护说明

- 当 memory/INDEX.md 新增 IMPORTANT 条目时，同步更新本文件匹配规则表
- 当候选通过 skill-review promote 后，预警自动消失（status 变为 promoted）
- v3.2：候选预警改为实际调用 skill-tracker 命令（M3修复）

````
