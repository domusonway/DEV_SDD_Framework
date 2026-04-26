---
id: context-probe
version: 3.3.0
recommended: true
changelog: memory/skill-changelog.md
last_updated: 2026-03-31
---

# SKILL: context-probe
> 任务：读取用户任务描述，自动匹配并加载相关 memory 条目
> v3.3：Step 3 升级为候选临时激活（TASK-ANN-02），支持 auto_attach 机制

---

## 触发时机

启动协议 Step 2.5 完成后，用户描述任务时立即执行。

---

## 执行步骤

### Step 0: 优先使用可执行 helper

```bash
python3 .claude/tools/context-probe/run.py "<用户任务描述>" --json
```

若需要记录自动加载的记忆使用效果：

```bash
python3 .claude/tools/context-probe/run.py "<用户任务描述>" --project <PROJECT> --record-loaded --json
```

该 helper 输出 `matched_dimensions`、`auto_load`、`skipped`、`candidate_domains`，并可将自动加载项写入项目 `memory/memory_usage.jsonl`，作为后续 effectiveness/pruning 的输入。

若需要按任务文本检索已有记忆，优先使用：

```bash
python3 .claude/tools/memory-search/run.py "<用户任务描述>" --project <PROJECT> --top-k 5 --json
```

需要把命中的记忆记录为 loaded 事件时追加 `--record-loaded`。

需要更强语义召回时使用 Bailian embedding 混合检索：

```bash
python3 .claude/tools/memory-search/run.py "<用户任务描述>" --project <PROJECT> --mode hybrid --top-k 5 --json
```

语义检索默认从根目录 `config.yaml` 读取非密钥模型配置，从 `.env` 或环境变量读取 `DASHSCOPE_API_KEY`。默认模型为 `text-embedding-v4`（北京地域有 100 万 Token 免费额度），并把向量缓存到 `.cache/dev_sdd/memory_vectors.sqlite`。可用 `MEMORY_SEARCH_EMBEDDING_MODEL`、`MEMORY_SEARCH_EMBEDDING_DIMENSIONS`、`MEMORY_SEARCH_LLM_MODEL` 临时覆盖 `config.yaml`。

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

---

### Step 3: 候选临时激活（v3.3 升级，TASK-ANN-02）

> 此步骤替代旧版 v3.2 的"候选预警"，实现更强的知识加速复用。

**执行方式**：运行以下命令，查找当前任务维度匹配的 `auto_attach: true` 候选：

```bash
python3 .claude/tools/skill-tracker/tracker.py candidates \
    --status pending_review \
    --auto-attach \
    --domain <当前匹配维度对应的 domain> \
    2>/dev/null | head -50
```

domain 与任务维度的对应关系：

| 当前任务维度 | 匹配的 domain |
|------------|--------------|
| 网络编程 / 异步网络 | network_code |
| TDD 问题 | tdd_patterns |
| 类型安全 | type_safety |
| 多线程 | concurrency |
| HTTP 协议 | http |
| 框架改进 | agent_workflow |

**临时激活输出格式**（若有匹配的 `auto_attach: true` 候选）：

对每个匹配候选，将其 `proposed_diff` 内容作为临时规则直接注入上下文：

```
[TEMP_RULE from HOOK_CAND_SDD-TINYHTTPD_001]
规则来源: hook-observer（confidence: medium，已在 2 个项目验证）
临时规则内容:
  network-guard 的触发条件应扩展覆盖 asyncio 相关代码：
  - asyncio.StreamReader / StreamWriter 需要触发 network-guard
  - 检查 reader.at_eof() 而非 b'' 判断
  - writer.drain() 必须 await，writer.close() + wait_closed() 在 finally 中

⚠️ 此为候选临时规则，尚未正式 promote。本次会话中视同正式规则执行。
   若本项目验证无副作用，请在交付后运行 skill-tracker validate 追加验证。
[/TEMP_RULE]
```

**规则**：
- 只展示 `auto_attach: true` + `status: pending_review` + `confidence >= medium` 的候选
- 每次最多激活 3 条临时规则（防止上下文过载）
- 优先激活 `confidence: high` 的候选
- `confidence: low` 的候选**不**临时激活（单次观察，尚不可靠）

**与旧版预警的区别**：

| 旧版 v3.2（预警） | 新版 v3.3（临时激活） |
|-----------------|-------------------|
| 只展示提示，不执行 | 将 proposed_diff 作为约束注入 |
| Agent 可忽略 | Agent 本次会话中必须遵守 |
| 需 `validated_projects ≥ 2` | 同上，且需 `auto_attach: true` |

若 `skill-tracker` 命令不存在或 `candidates/` 为空，静默跳过，不报错。

---

### Step 4: 输出加载确认

格式固定，必须输出：

```
[CONTEXT-PROBE]
匹配维度: <识别出的维度，多个用逗号分隔>
自动加载: <MEM_ID 列表或 SKILL 路径，或"仅 CRITICAL">
跳过加载: <因上限截断的条目，无则省略此行>
临时规则: <N 条激活 / 无>
[/CONTEXT-PROBE]
```

---

## 与启动协议的衔接

context-probe 的输出写入当前 session 文件的 `加载记忆` 字段。
激活的临时规则同步写入 `加载记忆` 字段，标注 `[TEMP]` 前缀。
HANDOFF.json 存在时，优先根据 `context_notes` 字段补充加载。

---

## 局限性说明

context-probe 是关键词匹配，有误判可能。
遇到误判时：直接告诉 Claude "加载 MEM_F_XXX"，手动覆盖自动加载结果。
临时规则若在本项目中造成问题，可通过 `tracker.py detach <id>` 取消附加。

---

## 维护说明

- 当 memory/INDEX.md 新增 IMPORTANT 条目时，同步更新本文件匹配规则表
- 当候选通过 skill-review promote 后，对应的临时规则自动消失（status 变为 promoted）
- v3.3：Step 3 从"候选预警"升级为"候选临时激活"（TASK-ANN-02）
- v3.2：候选预警改为实际调用 skill-tracker 命令（M3修复）
