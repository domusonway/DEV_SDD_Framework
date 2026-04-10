# /DEV_SDD:init — 从项目 CONTEXT 引导初始化执行文档

## 用法
```bash
/DEV_SDD:init
/DEV_SDD:init <project-name>
/DEV_SDD:init <project-path>
```

## 定位
- `/DEV_SDD:init` 是**项目引导初始化命令**：它从目标项目的 `docs/CONTEXT.md` 派生最小可执行文档集。
- 在共享命令契约中，本命令对应逻辑命名 `INIT`。
- 本命令只写入**项目作用域**内容：`projects/<PROJECT>/...`（或显式指定的项目根目录）；不会把 root `docs/*` 当作项目模板。
- helper CLI 负责解析 CONTEXT、生成 `docs/plan.json` 及派生文档、检查覆盖冲突，并输出 `{status,message,data}`。
- 当前 helper 入口：`python3 .claude/tools/init/run.py [project-name-or-path] [--json] [--dry-run] [--confirm-overwrite <token>]`。

## 输入来源
1. 目标项目根目录
2. `docs/CONTEXT.md`（初始化唯一必需输入）
3. 项目路径下已存在的目标文件（仅用于覆盖检测与 diff 预览）

### `docs/CONTEXT.md` 的模块划分约定
- 直接模块：可使用 `### <module-name>`，并在标题下提供字段清单（例如 `- 职责/- 输入/- 输出/- 依赖`）
- 分组 + 子模块：可使用 `### backend/`、`### frontend/` 这类分组标题，再在其下用 `#### <module-name>` 定义真正模块
- INIT 只会把带字段清单的标题当作可执行模块；纯分组标题不会写入 `docs/plan.json`
- 对于分组下的模块，INIT 会将其 SPEC 路径生成为 `modules/<group>/<module>/SPEC.md`
- `modules/` 默认承载规格文档；实现代码路径与 SPEC 路径是两个独立概念
- INIT 会在 `plan.json` 中为每个模块生成：
  - `spec_path`: 规格文件路径，默认 `modules/<...>/SPEC.md`
  - `impl_path`: 实现代码路径；若 `CONTEXT.md` 的目录结构能推断，则使用真实代码目录，否则回退到模块目录
- 为兼容旧工具，`path` 当前仍保留为 `impl_path` 的别名，但新规则以 `impl_path` 为准

## 生成/维护的目标
- `docs/plan.json` ← 执行状态真相源
- `docs/PLAN.md` ← `plan.json` 的只读派生视图
- `docs/TODO.md` ← 项目级备注/审计记录
- `CLAUDE.md` ← 项目入口与加载地图
- `AGENTS.md` ← 指向项目 `CLAUDE.md`
- `README.md` ← 项目简介与初始化约定
- `env/` ← Ubuntu 运行环境目录，包含 `README.md`、`requirements.txt`、`environment.yml`、`start.sh`

## 执行步骤
1. 解析目标项目：
   - 若提供 `<project-name>`，按 `projects/<project-name>/` 解析
   - 若提供 `<project-path>`，直接使用该项目根目录
   - 若未提供参数，则回退到当前激活项目
2. 读取 `docs/CONTEXT.md`，提取：
   - 项目标题/目标/背景
   - 技术栈摘要
   - 模块划分与依赖
3. 生成结构化 `docs/plan.json`：
    - `plan.json` 作为 INIT 的核心输出与后续命令真相源
    - 模块信息来自项目 `docs/CONTEXT.md`，而不是 root `docs/*`
    - `plan.json` 中模块条目必须显式区分 `spec_path` 与 `impl_path`
4. 生成派生文档：
    - `docs/PLAN.md` 与 `docs/TODO.md`
    - `CLAUDE.md`、`AGENTS.md`、`README.md`
    - `env/README.md`、`env/requirements.txt`、`env/environment.yml`、`env/start.sh`
5. 检查现有文件冲突：
   - 若目标文件不存在 → 直接创建
   - 若目标文件已存在且内容一致 → 视为 maintain
   - 若目标文件已存在且内容不同 → 返回 confirmation metadata 与 diff preview
6. 仅在满足以下条件时才允许覆盖：
   - 用户明确要继续 INIT
   - helper 返回的 `confirmation.token` 被回传给 `--confirm-overwrite`
7. 输出结果：
   - 始终使用 `{status,message,data}`
   - `data` 至少包含目标项目、来源 `docs/CONTEXT.md`、`writes`、`dry_run`
   - 冲突时额外包含 `confirmation.required/token/conflicts/diff_preview/next_action`

## 预期输出
```json
{
  "status": "ok",
  "message": "INIT 已完成：项目引导文档和 plan.json 已生成",
  "data": {
    "project": "demo-project",
    "source_context": "projects/demo-project/docs/CONTEXT.md",
    "plan_source": "docs/plan.json",
    "dry_run": false,
    "writes": [
      {"path": "docs/plan.json", "action": "create"},
      {"path": "docs/PLAN.md", "action": "create"}
    ]
  }
}
```

冲突时：
```json
{
  "status": "warning",
  "message": "检测到现有初始化目标与生成内容冲突，需确认后才能覆盖",
  "data": {
    "confirmation": {
      "required": true,
      "token": "abc123def456",
      "conflicts": [{"path": "CLAUDE.md", "reason": "existing_content_differs"}],
      "diff_preview": ["--- current/CLAUDE.md", "+++ generated/CLAUDE.md"],
      "next_action": "使用 --confirm-overwrite abc123def456 重新执行 INIT"
    }
  }
}
```

## 注意事项
- `docs/plan.json` 始终是执行状态真相源；生成的 markdown 视图不能反过来覆盖它。
- `--dry-run` 只返回即将写入/覆盖的计划，不实际修改文件，适合测试和人工确认。
- 若缺少 `docs/CONTEXT.md`，helper 返回 `error`，因为 INIT 无法安全推导项目引导文档。
- INIT 只处理 bootstrap/overwrite-confirmation 行为；后续计划重定义、TODO 协调、开始工作、修复流程分别由 `REDEFINE`、`UPDATE_TODO`、`START_WORK`、`FIX` 负责。
- 运行环境模板默认仅考虑 Ubuntu + conda：`env/start.sh` 应能在 Ubuntu shell 中创建/激活 conda 环境并进入项目目录。
