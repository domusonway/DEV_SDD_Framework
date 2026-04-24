````markdown
# DEV SDD Framework · 主入口

> 版本: v3.1 | 双仓库 · 单 .claude · 按需加载 · 会话快照 · Meta-Skill Loop

***

## ⚡ 启动协议（每次对话第一步，必须完整执行）

```
Step 1: 读取 memory/INDEX.md          → 加载框架 CRITICAL 规则（60秒内扫完）

Step 2: 检查下方「当前激活项目」字段
        有值 → 读取 projects/<PROJECT>/CLAUDE.md
               读取 projects/<PROJECT>/memory/INDEX.md
        无值 → 跳过，纯框架模式

Step 2.5: 【新增】检查 projects/<PROJECT>/memory/sessions/ 最新文件
          若存在 status: in-progress 的文件 →
              输出 [RESUME] 标记（格式见 PROJECT_RULES.md 规则一）
              并告知用户上次任务、中断点、下次继续
          若无 in-progress 文件 →
              输出 [NEW SESSION] 标记
          执行 context-probe：读取用户任务描述，自动匹配记忆 + 候选预警
              → 读取 .claude/skills/context-probe/SKILL.md

Step 3: 输出确认语：
        "[SDD就绪] 框架v3.1 | CRITICAL:5条 | 项目:<名称或无> | 等待任务"
```

> ⚠️ 未输出确认语 = 启动未完成，重新执行 Step 1
> ⚠️ Step 2.5 是强制步骤，不得以"无上次进度"为由跳过检查

***

## 当前激活项目

```
PROJECT: lument_server
PROJECT_PATH: projects/lument_server
```

> 切换项目：修改上方 PROJECT 字段，或使用 /project:switch
> 工作启动：优先使用 /DEV_SDD:start-work（可选 `<project-name>`）统一加载上下文、判断续接状态并选择下一步动作

***

## 框架级强制规则（内联，读到即生效）

1. **先规格再实现** — 任何代码前必须有 BRIEF.md 或 SPEC.md
2. **TDD驱动，根据BRIEF.md或SPEC.md编写测试代码，再进行开发**
3. **测试失败只改实现** — 禁止修改断言、禁止 skip，测试是规格的唯一表达
4. 每个功能的对应实现代码，不能是dummy，必须是能运行，保证功能与需求符合、且性能最佳
5. **关注并执行 memory 沉淀的相关规则和管线**
6. **【新增】每个决策节点产出 CHECKPOINT，对话结束前产出 SESSION-END**
7. **【新增】项目交付后激活 Meta-Skill Loop，生成框架改进候选供人工审核**
8. **【新增】任何 implement / fix / refactor 在 GREEN + VALIDATE 后，必须输出 Sedimentation Decision**：`no_sedimentation | project_memory | framework_candidate` 三选一，并给出一句理由；若非 `no_sedimentation`，必须立即写入项目 memory 或候选草稿

***

## 按需加载地图

| 当前任务               | 读取路径                                         |
| ------------------ | -------------------------------------------- |
| 任何任务开始             | `memory/INDEX.md`                            |
| 查看任务级实现细节         | `projects/<PROJECT>/docs/sub_docs/`          |
| 任务描述后自动匹配记忆        | `.claude/skills/context-probe/SKILL.md`      |
| 收到开发任务             | `.claude/skills/complexity-assess/SKILL.md`  |
| TDD 实现阶段           | `.claude/skills/tdd-cycle/SKILL.md`          |
| 出现 Bug / RED > 2 次 | `.claude/skills/diagnose-bug/SKILL.md`       |
| 所有测试 GREEN 后       | `.claude/skills/validate-output/SKILL.md`    |
| 任何 fix/implement/refactor 完成验证后 | `.claude/skills/memory-update/SKILL.md`      |
| 涉及 HTTP 协议         | `memory/domains/http/INDEX.md`               |
| 涉及 asyncio/异步网络    | `memory/domains/concurrency/INDEX.md`        |
| 涉及 bytes/str 错误    | `memory/domains/type_safety/INDEX.md`        |
| TDD 流程失败/测试设计      | `memory/domains/tdd_patterns/INDEX.md`       |
| H 模式多模块规划          | `.claude/agents/planner.md`                  |
| 写任何网络代码后           | `.claude/hooks/network-guard/HOOK.md`（立即执行）  |
| RED 超过 2 次         | `.claude/hooks/stuck-detector/HOOK.md`（立即执行） |
| 所有测试 GREEN         | `.claude/hooks/post-green/HOOK.md`（立即执行）     |
| 对话结束前              | `.claude/hooks/session-snapshot/HOOK.md`     |
| **项目交付后（新增）**      | `.claude/agents/memory-keeper.md`（含 Meta-Skill Loop）|
| **审核框架候选（新增）**     | `/project:skill-review`                      |

***

## 复杂度分流（收到任务后第一步）

| 分数  | 模式   | 文档要求                     | 记忆加载策略          |
| --- | ---- | ------------------------ | --------------- |
| 0–3 | L 轻量 | BRIEF.md ≤15 行           | CRITICAL 内联已足够  |
| 4–7 | M 标准 | CONTEXT.md + 各模块 SPEC.md | CRITICAL + 匹配领域 |
| 8+  | H 完整 | 完整文档 + Agent 流水线         | 按需全量            |

***

## Hook 触发规则（自动，无需人工记忆）

| 时机                        | Hook                | 不可跳过原因                |
| ------------------------- | ------------------- | --------------------- |
| 写任何含 recv/send/socket 代码后 | `network-guard`     | MEM\_F\_C\_004/005 验证 |
| RED 状态连续超过 2 次            | `stuck-detector`    | 防止在错误方向无限循环           |
| 所有测试变 GREEN               | `post-green`        | 触发验证 + Sedimentation Decision + hook-observer |
| 任意决策完成 / 对话结束前            | `session-snapshot`  | 过程记录不依赖流程走完           |
| **项目交付后（新增）**             | `hook-observer`     | 检测 Hook 触发健康度          |
| **项目交付后（新增）**             | `permission-auditor`| 检测权限边界健康度             |
| **promote 后（新增）**         | `test-sync`         | 确保新规则有测试覆盖            |

***

## Agent 分工（H 模式启用）

```
.claude/agents/planner.md         → 依赖拓扑分析，输出实现批次
.claude/agents/implementer.md     → 按批次执行 TDD（含 hook-observer 集成）
.claude/agents/reviewer.md        → 代码复审（含 hook-observer + test-sync）
.claude/agents/memory-keeper.md   → 项目完成后沉淀记忆 + 激活 Meta-Skill Loop
.claude/agents/agent-auditor.md   → 分析 Agent 协作缺口（新增）
.claude/agents/meta-skill-agent.md→ 生成全类型框架改进候选（新增）
```

***

## Meta-Skill Loop（v3.1 新增）

框架自进化机制，对应 HyperAgents metacognitive self-modification：

```
执行历史
    ↓（6类观察器）
candidates/ 候选池
    ↓（/project:skill-review 人工审核）
skill-tracker promote
    ↓（自动写入 + test-sync）
SKILL.md / HOOK.md / agents/*.md / tools/*.py / settings.local.json
    ↓
skill-changelog.md 版本追踪
```

**观察器覆盖范围**：
- `meta-skill-agent` → SKILL 规则候选
- `hook-observer` → Hook 触发条件候选
- `agent-auditor` → Agent 协作缺口候选
- `check_tools.sh` → Tool 功能缺失候选
- `permission-auditor` → 权限边界候选
- `test-sync` → 测试覆盖缺口候选

**安全边界**：候选只写入 `memory/candidates/`，不自动修改任何 `.claude/` 文件。
所有提升操作经人工审核（`/project:skill-review`）后执行。

***

## 项目 ↔ 框架 记忆边界

```
写入 projects/<n>/memory/sessions/  ← 会话过程快照（按领域命名，时间写入 frontmatter）
写入 projects/<n>/memory/           ← 此项目特有，换项目不适用
写入 memory/candidates/             ← 候选池（人工审核后升级至框架）← 新增
写入 memory/                        ← 跨项目通用，≥3个项目验证后升级至此
```

> 记忆沉淀路径：对话快照 → 项目 Bug/决策 memory → candidates 候选池
>   → （人工审核）→ 框架 memory

***

## 每日验证（可选但推荐）

```bash
bash .claude/hooks/verify-rules/check.sh
```

工作结束时运行，30 秒内确认当日记录是否完整（含候选积压状态）。

````
