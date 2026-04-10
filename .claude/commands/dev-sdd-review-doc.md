# /DEV_SDD:review_doc — 审查模块 SPEC 对 CONTEXT 的覆盖质量

## 用法
```bash
/DEV_SDD:review_doc
/DEV_SDD:review_doc <project-name>
/DEV_SDD:review_doc <project-path>
```

## 定位
- `/DEV_SDD:review_doc` 是**项目文档审查命令**：用于确认 `modules/**/SPEC.md` 是否覆盖 `docs/CONTEXT.md` 中定义的模块功能。
- 在共享命令契约中，本命令对应逻辑命名 `REVIEW_DOC`。
- 命令只读，不改写项目文档；其职责是输出可执行的审查结论和缺口清单。
- helper CLI 入口：`python3 .claude/tools/review-doc/run.py [project-name-or-path] [--json]`。

## 输入来源
1. 目标项目根目录
2. `docs/CONTEXT.md`
3. `modules/**/SPEC.md`

## 审查目标
- 按 `docs/CONTEXT.md` 中 `## 模块划分` 的机器可读条目逐模块检查
- 确认每个模块的 `职责 / 输入 / 输出 / 依赖` 是否在对应 SPEC 中得到覆盖
- 评估 SPEC 是否足够：
  - `具体`：包含明确接口、类型、行为或规则，而不是仅有泛化描述
  - `严谨`：包含约束、边界、错误路径或精确规则
  - `可执行`：包含测试最小集合、验收标准或可直接驱动 TDD 的描述
- 汇总 union 视角的缺口：缺失 SPEC、额外 SPEC、未覆盖字段、质量不足模块

## 执行步骤
1. 解析目标项目（显式参数优先，否则回退到当前激活项目）。
2. 读取 `docs/CONTEXT.md`，定位 `## 模块划分` 并提取每个模块的 `职责 / 输入 / 输出 / 依赖`。
3. 扫描 `modules/**/SPEC.md`，按模块名建立映射。
4. 逐模块审查：
   - 若缺失 SPEC → 标记 warning
   - 若存在多个同名 SPEC → 标记 warning
   - 若 SPEC 对 CONTEXT 字段覆盖不足 → 标记 warning 并列出缺口
   - 若 SPEC 缺少可执行的接口/规则/测试信号 → 标记 warning 并列出质量问题
5. 输出 `{status,message,data}`，其中 `data` 至少包含：
   - `project`, `project_root`
   - `context_source`
   - `summary`（模块总数、通过数、告警数）
   - `modules`（每个模块的审查结果）
   - `orphan_specs`（有 SPEC 但 CONTEXT 未声明的模块）

## 预期输出
```json
{
  "status": "warning",
  "message": "REVIEW_DOC 完成：9 个模块中 3 个存在覆盖或质量缺口",
  "data": {
    "project": "demo-project",
    "context_source": "docs/CONTEXT.md",
    "summary": {
      "total_modules": 9,
      "passed_modules": 6,
      "warning_modules": 3,
      "missing_specs": 1
    },
    "modules": [
      {
        "module": "cli",
        "status": "warning",
        "coverage": {
          "covered": false,
          "missing_fields": ["输入", "输出"]
        },
        "quality": {
          "specific": false,
          "rigorous": false,
          "executable": true
        }
      }
    ],
    "orphan_specs": []
  }
}
```

## 注意事项
- `review_doc` 只审查文档契约，不执行测试、不修改 SPEC、不自动重写 CONTEXT。
- 以 `docs/CONTEXT.md` 的 `## 模块划分` 为权威来源；若该节缺失或不可解析，helper 返回 `error`。
- 若项目存在嵌套模块目录，审查范围仍是 `modules/**/SPEC.md`。
- 该命令适合在 `INIT` 后、实现前或大范围重构后执行，用于提前发现 SPEC 漏项与歧义。
