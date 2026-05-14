# Challenger Agent BRIEF

- 目标：新增 `Challenger` 质疑者 agent，在长任务、复杂任务和交付结论前对需求满足度、证据充分性和用户场景最优性做反向质询。
- 范围：框架 agent、hook、context-probe 路由、H/M 模式流程和会话记录；不替代 Reviewer 的代码审查职责。
- 输入：用户原始需求、阶段分析过程摘要、验证证据、主模型草稿结论、当前复杂度/阶段。
- 输出：结构化 `[CHALLENGER]` 块与 `<PROJECT_ROOT>/memory/challenges/<session-slug>.md` 质疑记录（`PROJECT_PATH` 优先）。
- 角色视角：产品经理、验收经理、真实用户。
- 触发：H 模式、M 模式跨模块、Planner 计划后、Reviewer 交付前、post-green 后、RED>2 后、跨 session 续接和“完成/最优/交付就绪”结论词。
- 决策：`pass | pass_with_risk | rework | ask_user`。
- 约束：每次最多 7 个问题，最多 3 个阻塞问题，必须引用具体需求/证据/结论，不得泛泛质疑或扩大需求。
- 验收1：`Challenger` agent 文档包含输入、角色、输出、阻塞规则和噪声控制。
- 验收2：`challenge-gate` hook 文档明确强制/建议触发条件和结构化记录路径。
- 验收3：现有 Planner、Implementer、Reviewer、post-green、session-snapshot、context-probe 能路由到 Challenger。
- 验收4：`python3 .claude/hooks/challenge-gate/run.py ... --json` 能根据任务文本、阶段、复杂度、RED 次数、续接状态和证据摘要输出是否触发 Challenger。
- 验收5：质疑记录使用 AI-first 紧凑 schema，必须包含 `complexity_mode`、`user_scenario`、`problem_type`、`content_scope`、`claims/evidence/challenges` 和 `target_claim/evidence_refs` 绑定。
