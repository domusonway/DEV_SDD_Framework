# /DEV_SDD:update-todo — 维护 plan.json stable IDs（TODO 已废弃）

## 用法
```bash
/DEV_SDD:update-todo
/DEV_SDD:update-todo <project-name>
/DEV_SDD:update-todo <project-path>
/DEV_SDD:update-todo <project> --ids T-002,T-004
```

## 定位
- `docs/TODO.md` 已废弃，不再作为项目执行文档。
- `/DEV_SDD:update-todo` 保留为**稳定 ID 维护命令**：仅在 `docs/plan.json` 缺少任务 ID 时自动补齐。
- helper 入口：`python3 .claude/tools/update-todo/run.py [project-name-or-path] [--ids ...] [--json] [--dry-run]`

## 核心规则
1. `docs/plan.json` 是唯一执行真相源。
2. stable ID（如 `T-001`）是任务主键，不依赖任务名或位置。
3. 本命令不会写入 `docs/TODO.md`，也不会创建该文件。

## 预期输出
```json
{
  "status": "ok",
  "message": "UPDATE_TODO 已完成：仅维护 plan.json stable ID（未写入 docs/TODO.md）",
  "data": {
    "plan_source": "docs/plan.json",
    "deprecated": true,
    "writes": [
      {"path": "docs/plan.json", "action": "overwrite"}
    ]
  }
}
```
