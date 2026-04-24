# /DEV_SDD:redefine — 基于项目上下文重定义执行计划

## 用法
```bash
/DEV_SDD:redefine
/DEV_SDD:redefine <project-name>
/DEV_SDD:redefine <project-path>
```

兼容旧拼写（仅兼容入口，不分叉语义）：
```bash
/DEV_SDD:redefind
```

## 定位
- `/DEV_SDD:redefine` 是**计划重定义命令**：用于根据项目最新规划输入重建执行计划。
- 在共享命令契约中，本命令对应逻辑命名 `REDEFINE`。
- `projects/<PROJECT>/docs/plan.json` 始终是执行状态真相源，`docs/sub_docs/` 存放任务细节，`docs/PLAN.md` 仅为派生只读文档。
- helper CLI 负责读取项目输入、计算计划变化、按固定顺序更新文件，并输出 `{status,message,data}`。
- 当前 helper 入口：`python3 .claude/tools/redefine/run.py [project-name-or-path] [--json] [--dry-run] [--alias REDEFIND]`。

## 上游输入
1. 目标项目根目录
2. `projects/<PROJECT>/docs/CONTEXT.md`（或显式目标路径下 `docs/CONTEXT.md`）
3. 目标项目已有 `docs/plan.json`（用于保留未变模块状态并计算变化）

## 下游派生与传播顺序
REDEFINE 必须按以下顺序传播，禁止反向使用 markdown 作为源：

1. 更新 `docs/plan.json`（权威执行状态）
2. 基于最新 `plan.json` 重建 `docs/PLAN.md`（只读视图）
3. 基于最新 `plan.json` 重建 `docs/sub_docs/` 的任务文档索引骨架
4. 基于最新 `plan.json` 重建 `docs/PLAN.md`（只读视图）

> 任何差异判断、下一步动作和命令可见状态都应来自 `plan.json`，而不是旧 `PLAN.md`。

## 执行步骤
1. 解析目标项目（显式参数优先，否则回退到当前激活项目）。
2. 读取 `docs/CONTEXT.md` 作为重定义输入，提取模块与依赖关系。
3. 读取现有 `docs/plan.json`（若存在），保留未变模块状态并计算新增/移除/保留模块。
4. 生成新的 `docs/plan.json`。
5. 使用新 `plan.json` 重新生成 `docs/PLAN.md` 与 `docs/sub_docs/`。
6. 输出 `{status,message,data}`，其中 `data` 至少包含：
   - `project`, `project_root`
   - `input_source`（`docs/CONTEXT.md`）
   - `plan_source`（`docs/plan.json`）
   - `propagation`（固定顺序）
   - `writes`（每个目标文件的 create/maintain/overwrite）
   - `changes`（added/removed/preserved modules）

## 兼容别名 `REDEFIND`
- `REDEFIND` 仅是兼容入口别名，不得创建独立后端逻辑路径。
- 行为必须与 `REDEFINE` 完全一致，唯一差异是输出中附带 alias 提示元数据。
- helper 可通过 `--alias REDEFIND` 接收兼容入口，并映射到同一 REDEFINE 执行流。

## 预期输出
```json
{
  "status": "ok",
  "message": "REDEFINE 已完成：plan.json 已更新并重建派生文档",
  "data": {
    "project": "demo-project",
    "input_source": "docs/CONTEXT.md",
    "plan_source": "docs/plan.json",
    "propagation": [
      "update:docs/plan.json",
      "regenerate:docs/PLAN.md",
      "regenerate:docs/sub_docs/*"
    ],
    "writes": [
      {"path": "docs/plan.json", "action": "overwrite"},
      {"path": "docs/PLAN.md", "action": "overwrite"},
      {"path": "docs/sub_docs/feature/modules/<module>/<task_id>.md", "action": "create|overwrite"}
    ],
    "changes": {
      "added_modules": ["new-module"],
      "removed_modules": ["legacy-module"],
      "preserved_modules": ["core-module"]
    }
  }
}
```

## 注意事项
- 不得把 root `docs/PLAN.md` 或 root `docs/TODO.md` 用作项目执行状态源。
- 不得把项目 `docs/PLAN.md` 反向当作 `plan.json` 输入。
- `--dry-run` 只返回重定义结果预览，不实际改写文件。
- 若缺少目标项目或缺少 `docs/CONTEXT.md`，helper 返回 `warning`/`error` 并给出 `next_action`。
