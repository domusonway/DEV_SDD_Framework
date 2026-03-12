# DEV SDD Framework · 主入口

> 版本: v2.0 | 双仓库 · 单 .claude · 按需加载

---

## ⚡ 启动协议（每次对话第一步，必须完整执行）

```
Step 1: 读取 memory/INDEX.md          → 加载框架 CRITICAL 规则（60秒内扫完）
Step 2: 检查下方「当前激活项目」字段
        有值 → 读取 projects/<PROJECT>/CLAUDE.md
               读取 projects/<PROJECT>/memory/INDEX.md
        无值 → 跳过，纯框架模式
Step 3: 输出确认语：
        "[SDD就绪] 框架v2.0 | CRITICAL:5条 | 项目:<名称或无> | 等待任务"
```

> ⚠️ 未输出确认语 = 启动未完成，重新执行 Step 1

---

## 当前激活项目

```
PROJECT: structured-light-stereo
PROJECT_PATH: projects/structured-light-stereo
```

> 切换项目：修改上方 PROJECT 字段，或使用 /project:switch

---

## 框架级强制规则（内联，读到即生效）

1. **先规格再实现** — 任何代码前必须有 BRIEF.md 或 SPEC.md
2. **接口类型必须精确** — bytes / str / int 不能含糊，混用在 socket 层必报错
3. **测试失败只改实现** — 禁止修改断言、禁止 skip，测试是规格的唯一表达
4. **网络 recv 必须精确捕获** — `except (socket.timeout, ConnectionResetError, OSError)` 禁用 `except Exception`
5. **socket 发送必须是 bytes** — `recv` 返回 `b''` 表示连接关闭，必须 `if not data: break`

---

## 按需加载地图

| 当前任务              | 读取路径                                           |
| --------------------- | -------------------------------------------------- |
| 任何任务开始          | `memory/INDEX.md`                                  |
| 收到开发任务          | `.claude/skills/complexity-assess/SKILL.md`        |
| TDD 实现阶段          | `.claude/skills/tdd-cycle/SKILL.md`                |
| 出现 Bug / RED > 2 次 | `.claude/skills/diagnose-bug/SKILL.md`             |
| 所有测试 GREEN 后     | `.claude/skills/validate-output/SKILL.md`          |
| 项目完成后            | `.claude/skills/memory-update/SKILL.md`            |
| 涉及 HTTP 协议        | `memory/domains/http/INDEX.md`                     |
| H 模式多模块规划      | `.claude/agents/planner.md`                        |
| 写任何网络代码后      | `.claude/hooks/network-guard/HOOK.md`（立即执行）  |
| RED 超过 2 次         | `.claude/hooks/stuck-detector/HOOK.md`（立即执行） |
| 所有测试 GREEN        | `.claude/hooks/post-green/HOOK.md`（立即执行）     |

---

## 复杂度分流（收到任务后第一步）

| 分数 | 模式   | 文档要求                    | 记忆加载策略        |
| ---- | ------ | --------------------------- | ------------------- |
| 0–3  | L 轻量 | BRIEF.md ≤15 行             | CRITICAL 内联已足够 |
| 4–7  | M 标准 | CONTEXT.md + 各模块 SPEC.md | CRITICAL + 匹配领域 |
| 8+   | H 完整 | 完整文档 + Agent 流水线     | 按需全量            |

---

## Hook 触发规则（自动，无需人工记忆）

| 时机                             | Hook             | 不可跳过原因            |
| -------------------------------- | ---------------- | ----------------------- |
| 写任何含 recv/send/socket 代码后 | `network-guard`  | MEM_F_C_004/005 验证    |
| RED 状态连续超过 2 次            | `stuck-detector` | 防止在错误方向无限循环  |
| 所有测试变 GREEN                 | `post-green`     | 触发验证 + 记忆沉淀判断 |

---

## Agent 分工（H 模式启用）

```
.claude/agents/planner.md       → 依赖拓扑分析，输出实现批次
.claude/agents/implementer.md   → 按批次执行 TDD
.claude/agents/reviewer.md      → 代码复审，调用 validate-output
.claude/agents/memory-keeper.md → 项目完成后沉淀记忆
```

---

## 项目 ↔ 框架 记忆边界

```
写入 projects/<n>/memory/    ← 此项目特有，换项目不适用
写入 memory/                 ← 跨项目通用，≥3个项目验证后升级至此
```

> 记忆沉淀路径：项目 Bug → 项目 memory → （验证通用性）→ 框架 memory
