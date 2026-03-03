# 新建项目指南（HOW_TO_START_PROJECT.md）

> 框架层文档。描述"如何基于此框架启动一个新项目"的完整流程。

---

## 框架 vs 项目 的分层

```
sdd-framework/                    ← 你现在看到的这个仓库（通用，不改）
  CLAUDE.md                       ← 框架规则（环境无关，项目无关）
  .claude/skills/                 ← 通用技能（自动触发）
  .claude/agents/                 ← 通用 subagent（按需调用）
  .claude/hooks/                  ← 通用强制保障
  memory/framework/               ← 跨项目通用经验
  modules/template/               ← 模块模板（空白）
  projects/template_project/      ← 项目配置模板（空白）
  docs/                           ← 框架级文档

projects/<your_project>/          ← 你填写的项目层（每个项目不同）
  CLAUDE.md                       ← @import CONTEXT.md，项目特有规则
  CONTEXT.md                      ← 领域知识 + 环境约束 + 反模式清单
  memory/                         ← 项目特有经验
  modules/<m>/SPEC.md             ← 项目模块规格
  DIAGNOSIS/                      ← 生产 Bug 报告
```

---

## Step 1：复制项目模板

```bash
cp -r projects/template_project projects/<your_project_name>
```

---

## Step 2：填写 CONTEXT.md（最重要的一步）

`projects/<your_project>/CONTEXT.md` 是防止 Agent 偏离的核心文档。
必须在任何模块开发前完成以下内容：

```
§1 领域知识前提   — Agent 不懂领域时会犯的错
§2 依赖约束       — 运行环境、库版本及"为什么是这个版本"
§3 反模式清单     — 已知禁止做法（随 Bug 修复持续更新）
§4 设计决策溯源   — 参考项目"为什么这样设计"
§5 模块间隐式契约 — 接口定义里看不到的模块间约定
```

---

## Step 3：更新项目 CLAUDE.md

```markdown
# <your_project> 项目上下文

@CONTEXT.md
@../../memory/INDEX.md

## 项目特有规则（覆盖框架默认值时说明原因）
- 运行环境：`<your_env_command>`
```

---

## Step 4：注册项目 Memory 索引

在 `memory/INDEX.md` 的项目表中添加一行：
```markdown
| <your_project> | [→](projects/<your_project>/INDEX.md) |
```
创建 `memory/projects/<your_project>/INDEX.md`（复制 template）。

---

## Step 5：启动 @planner

```
@planner 分析 reference_project/ 目录，完成 CONTEXT.md 和模块 SPEC
```

---

## Step 6：TDD 开发循环（按模块重复）

```
@tester 为 <module> 生成 fixtures 和校验器
@implementer 实现 <module>（TDD 循环）
@reviewer 复审 <module>
```

---

## Step 7：生产维护

有 Bug 时，按 `DIAGNOSIS/BUG_REPORT_TEMPLATE.md` 填写报告，然后：
```
@diagnostician 诊断 DIAGNOSIS/BUG_REPORT_<id>.md
```

---

## 哪些内容属于框架层，哪些属于项目层

| 内容 | 所在层 | 判断依据 |
|------|--------|---------|
| TDD 循环流程 | 框架 | 任何项目都适用 |
| 校验器自测原则 | 框架（CRITICAL Memory）| 任何项目都适用 |
| 运行环境命令 | 项目（CONTEXT.md §2）| 每个项目不同 |
| 领域数据格式约定 | 项目（CONTEXT.md §1）| 每个项目不同 |
| 特定版本 Bug | 项目（CONTEXT.md §2）| 特定依赖版本 |
| Bug 修复经验 | 项目 Memory | 与具体代码相关 |
| 反模式清单 | 项目（CONTEXT.md §3）| 由项目 Bug 积累 |
