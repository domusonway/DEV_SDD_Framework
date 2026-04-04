# /DEV_SDD:update-todo — 按 stable ID 合并项目 TODO

## 用法
```bash
/DEV_SDD:update-todo
/DEV_SDD:update-todo <project-name>
/DEV_SDD:update-todo <project-path>
/DEV_SDD:update-todo <project> --ids T-002,T-004
```

## 定位
- `/DEV_SDD:update-todo` 是**TODO 同步/合并命令**：将项目 `docs/plan.json` 的权威执行状态同步到 `docs/TODO.md` 的工具管理区。
- 在共享命令契约中，本命令对应逻辑命名 `UPDATE_TODO`。
- `docs/plan.json` 保持唯一执行状态真相源；`docs/TODO.md` 是人类可读的项目跟进面板。
- helper CLI 负责 stable-ID 注入、部分更新、冲突检测和确认元数据输出。
- 当前 helper 入口：`python3 .claude/tools/update-todo/run.py [project-name-or-path] [--ids T-001,T-003] [--json] [--dry-run] [--confirm-overwrite <token>]`。

## 核心规则
1. **stable ID 是唯一 merge key**
   - 每个 `plan.json` 任务项必须有不可变 `id`（例如 `T-003`）。
   - 若任务缺少 `id`，helper 会按顺序补齐并写回 `docs/plan.json`。
   - 禁止按列表位置或文案文本作为主身份键。

2. **TODO 分区所有权**
   - 工具管理区：`<!-- DEV_SDD:MANAGED:BEGIN --> ... <!-- DEV_SDD:MANAGED:END -->`
   - 用户备注区：`<!-- DEV_SDD:USER_NOTES:BEGIN --> ... <!-- DEV_SDD:USER_NOTES:END -->`
   - UPDATE_TODO 默认只更新管理区；用户备注区按字节保持不变。

3. **部分更新优先**
   - 支持 `--ids T-002,T-004`，仅更新选中的 stable IDs。
   - 未选中的条目（包括人工补充的文本）必须保留。

4. **冲突必须确认**
   - 若检测到本地管理区编辑冲突、重复/异常 ID、不可安全重建等场景，helper 返回：
     - `status=warning`
     - `data.confirmation.required=true`
     - `data.confirmation.token`
     - `data.confirmation.conflicts[]`（逐项冲突详情）
   - 未携带正确 `--confirm-overwrite <token>` 时，禁止覆盖。

5. **全量重建限制**
   - 仅在 `docs/TODO.md` 缺失，或文件仍为可识别的历史生成基线时，允许直接全量生成 managed TODO。
   - 对用户手改且不可解析的 TODO，不允许静默全量覆盖，必须走 confirmation。

## 执行步骤
1. 解析目标项目（显式参数优先，否则使用当前激活项目）。
2. 读取 `docs/plan.json`，补齐/验证 stable IDs。
3. 读取 `docs/TODO.md`：
   - 若包含 managed + notes 标记，执行 stable-ID 局部合并；
   - 若缺失标记，判定是否可安全全量重建。
4. 若发现冲突，返回 confirmation metadata，不写文件。
5. 冲突确认后（`--confirm-overwrite token`）执行写入。
6. 输出统一 `{status,message,data}` envelope。

## 预期输出
```json
{
  "status": "ok",
  "message": "UPDATE_TODO 已完成：按 stable ID 更新 TODO 并保留用户备注区",
  "data": {
    "project": "demo-project",
    "plan_source": "docs/plan.json",
    "todo_path": "docs/TODO.md",
    "selected_ids": ["T-002", "T-004"],
    "writes": [
      {"path": "docs/plan.json", "action": "overwrite"},
      {"path": "docs/TODO.md", "action": "overwrite"}
    ]
  }
}
```

冲突时：
```json
{
  "status": "warning",
  "message": "检测到本地冲突或不可安全重建场景，需确认后才能覆盖",
  "data": {
    "confirmation": {
      "required": true,
      "token": "abc123def456",
      "conflicts": [
        {"reason": "local_managed_edit", "id": "T-003"}
      ],
      "next_action": "使用 --confirm-overwrite abc123def456 重新执行 UPDATE_TODO"
    }
  }
}
```

## 注意事项
- 不得把 `docs/TODO.md` 反向当作执行状态真相源。
- 不得静默覆盖用户备注区或本地冲突编辑。
- `--dry-run` 仅返回计划写入结果与冲突元数据，不落盘。
- 与 `REDEFINE` 的职责边界：`REDEFINE` 负责重定义并可重建 TODO；`UPDATE_TODO` 负责 stable-ID 粒度同步与冲突可控合并。
