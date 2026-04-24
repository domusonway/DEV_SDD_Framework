# /DEV_SDD:fix — 先 triage，再给出双层修复选项

## 用法
```bash
/DEV_SDD:fix <issue-json-path>
```

helper 入口：
```bash
python3 .claude/tools/fix/run.py <issue-json-path> [--json] [--dry-run]
```

## 定位
- `/DEV_SDD:fix` 是**修复分诊命令**：它负责读取 issue、项目上下文、项目 memory 和可用计划信息，先做 triage，再给出修复选项。
- 在共享命令契约中，本命令对应逻辑命名 `FIX`。
- 本命令只输出 triage/option 建议，不直接改业务代码，也不改 `docs/plan.json`、`docs/PLAN.md` 或 `docs/sub_docs/*`。
- helper CLI 使用共享 `{status,message,data}` envelope。

## 必需输入
issue JSON 至少应提供：
- `project`：项目名或项目路径（显式优先；缺失时回退到当前激活项目）
- `title`
- `summary`

推荐额外提供：
- `symptoms`
- `expected_behavior`
- `actual_behavior`
- `reproduction_steps`
- `module_hints`
- `file_hints`
- `suspected_impact`
- `log_excerpt`

## 执行步骤
1. 解析 issue JSON。
2. 按 `start-work` 风格解析目标项目：
   - 显式 `project` 路径/名称优先
   - 缺失时回退到当前激活项目
3. 在提出修复建议前，必须先读取：
   - 项目上下文：优先 `projects/<PROJECT>/docs/CONTEXT.md`，再回退 `CLAUDE.md` / `README.md`
   - 项目记忆：`projects/<PROJECT>/memory/INDEX.md`
   - 计划信息：`docs/plan.json` → `docs/PLAN.md` → `docs/IMPLEMENTATION_PLAN.md`
4. 生成 triage 摘要：
   - 问题是否可复现
   - 当前 confidence（`high` / `medium` / `low`）
   - likely modules / files
   - impact / regression scope
   - 相关 memory 信号（约束、已知 bug、设计决策）
   - 缺失上下文（若有）
5. 在 triage 之后，固定输出两层 option family：
   - `minimal_change`
   - `comprehensive_change`
6. 每个 option 至少包含：
   - `summary`
   - `files_or_modules`
   - `risks`
   - `regression_scope`
   - `why`
7. 输出 memory sedimentation follow-up：
   - 若修复可能产生新的可复用经验，提示在验证通过后更新 `projects/<PROJECT>/memory/INDEX.md`

## 稀疏 issue 的降级规则
- 若缺少 `reproduction_steps`、`expected_behavior`、`actual_behavior` 等关键上下文：
  - 返回 `warning` 或低置信度 triage
  - 明确列出 `missing_context`
  - 仍保留 `minimal_change` / `comprehensive_change` 两层结构
  - 但 option 应以“补充上下文 / 诊断增强 / 观测收敛”为主，**不得幻觉式给出精确补丁**

## 预期输出
```json
{
  "status": "ok",
  "message": "FIX triage 已生成：demo-project | confidence=high | repro=reproducible",
  "data": {
    "project": "demo-project",
    "issue_source": "skill-tests/fixtures/fix/repro-issue.json",
    "context_sources": [
      "projects/demo-project/docs/CONTEXT.md",
      "projects/demo-project/CLAUDE.md"
    ],
    "memory_source": "projects/demo-project/memory/INDEX.md",
    "plan_source": "plan.json",
    "triage": {
      "summary": "问题起点更像在 calibration，且回归面至少覆盖 calibration, stripe_matching, reconstruction_3d。",
      "confidence": "high",
      "reproducibility": "reproducible",
      "likely_modules": ["calibration"],
      "missing_context": [],
      "memory_signals": {
        "known_constraints": ["..."],
        "known_bugs": ["..."],
        "decision_context": ["..."]
      }
    },
    "options": {
      "minimal_change": {
        "summary": "...",
        "files_or_modules": ["sls/calibration.py", "calibration"],
        "risks": ["..."],
        "regression_scope": ["calibration", "stripe_matching"],
        "why": "..."
      },
      "comprehensive_change": {
        "summary": "...",
        "files_or_modules": ["sls/calibration.py", "calibration", "stripe_matching"],
        "risks": ["..."],
        "regression_scope": ["calibration", "stripe_matching", "reconstruction_3d"],
        "why": "..."
      }
    },
    "memory_follow_up": {
      "recommended": true,
      "path": "projects/demo-project/memory/INDEX.md",
      "reason": "若本次修复沉淀出新的边界校验/回归经验，应在验证通过后更新项目 memory。"
    }
  }
}
```

## 注意事项
- FIX 的职责是 triage + optioning，不是直接 patch 应用。
- FIX 在推荐修复前必须先检查项目 memory；若 memory 存在，输出中必须体现已知约束/bug/决策。
- 对高风险问题，输出必须体现 impact / risk / regression trade-off，而不是只给一句“建议修复”。
- 若问题会改变规格、计划或用户维护的执行笔记，不应由 FIX 静默处理。
