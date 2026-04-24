# /DEV_SDD:start-work — 启动或续接当前工作流

## 用法
```bash
/DEV_SDD:start-work
/DEV_SDD:start-work <project-name>
/DEV_SDD:start-work <project-path>
```

## 定位
- `/DEV_SDD:start-work` 是**工作流启动命令**：用于统一加载上下文、判断续接状态、检查计划进度，并给出下一步动作。
- 在共享命令契约中，本命令对应逻辑命名 `START_WORK`。
- `/project:*` 是**项目/管理命令**：用于创建项目、切换项目、校验技能、记忆沉淀、候选审核等管理动作。
- 本命令使用辅助 CLI 执行核心探测：`python3 .claude/tools/start-work/run.py [project-name-or-path] [--json]`。
- slash-command 文档负责说明启动/续接语义、读取范围和降级原则；helper CLI 负责实际探测并输出结构化结果。

## 执行步骤
1. 确定目标项目：
   - 若提供 `<project-name>`，可先调用 `/project:switch <project-name>` 使其成为激活项目
   - 若提供 `<project-path>`（支持 repo-relative 或绝对路径），helper 直接对该路径执行**只读探测**，不要求先 switch
   - 若未提供参数，则使用当前激活项目
2. 读取框架入口上下文：
   - `memory/INDEX.md`
   - `AGENTS.md`
3. 若当前存在激活项目，继续读取：
   - `projects/<PROJECT>/CLAUDE.md`
   - `projects/<PROJECT>/memory/INDEX.md`
4. 检查续接状态：
   - 查看 `projects/<PROJECT>/memory/sessions/` 最新 session 文件
   - 若存在 `HANDOFF.json`，按 `.claude/hooks/context-budget/HOOK.md` 的 handoff 流程优先读取
   - 根据现有协议决定输出 `[RESUME]` 或 `[NEW SESSION]`
5. 执行 context-probe：
   - 读取用户当前任务描述
   - 自动匹配相关 memory / skill / 候选临时规则
6. 执行 complexity-assess：
   - 判断当前任务属于 L / M / H 模式
   - 明确下一步应进入的执行路径（直接 TDD / 逐模块实现 / Planner → Implementer → Reviewer）
7. 调用 helper CLI 汇总状态：
   ```bash
   python3 .claude/tools/start-work/run.py [project-name-or-path] --json
   ```
   - JSON 输出遵循共享 envelope `{status,message,data}`
   - `status` 仅使用 `ok` / `warning` / `error`
   - `message` 提供人类可读摘要；`data` 承载 `project`、`context_files`、`session`、`mode`、`plan`、`reconciliation`、`next_action`、`next_action_source`
   - helper 内部按优先级读取计划：`plan.json` → `PLAN.md` → `IMPLEMENTATION_PLAN.md`
   - helper 内部汇总：上下文文件、session/handoff 状态、模式检测、计划进度、next_action
8. 输出启动摘要：
   - 当前项目
   - Session 状态（RESUME / NEW SESSION）
   - 已加载记忆
   - 复杂度模式（L / M / H）
   - 当前计划状态
   - 推荐下一步动作

## 预期输出
```text
[START-WORK]
项目: <PROJECT>
Session: <RESUME | NEW SESSION>
加载: <memory / skill 摘要>
模式: <L | M | H>
计划: <当前进度摘要>
下一步: <推荐动作>
[/START-WORK]
```

## 注意事项
- 此命令负责**开始/恢复工作流**，不替代现有 `/project:*` 管理命令。
- 若检测到缺少项目上下文，应先通过 `/project:new` 或 `/project:switch` 建立正确的项目环境。
- 显式传入项目路径时，helper 可用于一次性 read-only 探测（例如外部项目排查）；不会写入任何项目文件，也不会自动切换激活项目。
- 若用户只是要查看候选/验证/切换项目，应继续使用对应的 `/project:*` 命令。
- helper 缺少项目/计划/session 数据时必须降级输出 warning，不允许崩溃。
- 缺少 session/handoff 时，helper 应降级为 `NEW SESSION`；缺少计划数据时，应按 `plan.json` → `PLAN.md` → `IMPLEMENTATION_PLAN.md` 回退并在输出中注明来源。
- 本命令是只读汇总命令，不负责替 `INIT`、`REDEFINE`、`UPDATE_TODO` 或 `FIX` 执行写操作；这些命令共享同一 `{status,message,data}` 契约，但各自的确认策略和写入权限单独定义。
