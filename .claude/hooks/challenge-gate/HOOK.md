# HOOK: challenge-gate
> 触发时机：长任务、复杂任务或交付结论前，判断是否必须激活 Challenger

---

## 目的

防止主模型在长链路执行后把“阶段性正确”误判为“满足用户原始需求”。该 hook 只决定是否触发 `.claude/agents/challenger.md`，不替代测试、Reviewer 或 validate-output。

---

## 适用范围

适用于 DEV SDD 框架内的规划、实现批次、验证、复审、交付和跨 session 续接阶段，尤其是 H/M 模式、长任务和包含“完成/最优/交付就绪”结论的场景。

---

## 规则

1. 命中强制触发条件时必须读取 Challenger。
2. Challenger 返回 `rework` 或 `ask_user` 时不得输出交付结论。
3. Challenger 返回 `pass_with_risk` 时最终回答必须写明残余风险。
4. 未命中触发条件时，应在关键 checkpoint 或最终报告中说明 `challenge-gate: 未触发`。

---

## 强制触发

| 场景 | 触发点 | 原因 |
|---|---|---|
| H 模式 | Planner 输出计划后；Reviewer 交付前 | 任务链路长，容易需求漂移 |
| M 模式跨 2 个以上模块 | 批次完成后或交付前 | 模块边界和验收证据容易遗漏 |
| Planner | 实现计划移交 Implementer 前 | 防止计划方向错误 |
| Reviewer | 输出“交付就绪”结论前 | 防止验收证据不足 |
| post-green | GREEN + VALIDATE 后声明完成时 | 测试通过不等于用户场景最优 |
| RED > 2 | stuck-detector 后准备继续时 | 防止在错误方向上继续投入 |
| 跨 session | 读取 in-progress / HANDOFF 后准备续接时 | 防止上下文丢失导致结论断层 |
| 结论词 | 出现“完成、交付、最优、最终结论、验收通过、ready” | 高风险确认语需要反向质询 |

---

## 建议触发

| 场景 | 触发点 |
|---|---|
| L 模式但用户明确要求“方案/评估/确认最优” | 最终回答前 |
| 长任务中间批次 | 进入下一批次前 |
| 重要架构/接口决策 | 写入 CHECKPOINT 前 |

---

## 不触发

- 简单解释、查命令、轻量单文件修改，且没有“最优/交付/验收”结论词。
- 用户明确要求快速回答且风险低。
- Challenger 已在同一阶段触发且没有新证据或新结论。

---

## 示例

正确：H 模式 Planner 输出批次后先触发 Challenger，若发现验收证据缺口则修正计划再交给 Implementer。

错误：Reviewer 看到测试通过后直接输出“交付就绪”，未检查用户原始目标、skip、未验证假设和残余风险。

---

## 执行步骤

1. 收集用户原始需求、当前阶段、主模型草稿结论、验证证据和最近 CHECKPOINT。
2. 优先执行可执行判定脚本：

```bash
python3 .claude/hooks/challenge-gate/run.py \
  --task "<用户原始需求>" \
  --stage "<planning|green|validate|review|delivery|session_end>" \
  --mode "<L|M|H>" \
  --evidence "<pytest/doc-template/validate-output 等证据摘要>" \
  --json
```

3. 若脚本输出 `triggered: true`，读取 `.claude/agents/challenger.md` 并执行。
4. 将 `[CHALLENGER]` 输出追加到当前响应或 session checkpoint。
5. 如项目存在，追加结构化记录到 `<PROJECT_ROOT>/memory/challenges/<session-slug>.md`（`PROJECT_PATH` 优先）。
6. 根据 `decision` 执行阻塞规则：`pass` 继续，`pass_with_risk` 带风险继续，`rework` 先返工，`ask_user` 先澄清。

---

## 噪声控制

- 每次最多 7 个问题。
- 每次最多 3 个阻塞问题。
- 每个问题必须引用具体需求、证据、结论或阶段状态。
- 不得扩大用户需求。
- 不得把主观偏好包装成阻塞问题。
- 没有实质问题时必须输出 `decision: pass`。

---

## 禁止行为

- 禁止为了质疑而质疑。
- 禁止提出没有证据锚点的泛泛问题。
- 禁止把新需求伪装成验收阻塞项。
- 禁止在 `rework` 或 `ask_user` 未处理前输出交付结论。

---

## 输出摘要

```markdown
[CHALLENGE-GATE]
triggered: yes | no
reason: <命中规则或跳过原因>
stage: <planning | green | validate | review | delivery | session_end>
challenger_decision: <pass | pass_with_risk | rework | ask_user | n/a>
record: <PROJECT_ROOT>/memory/challenges/<session-slug>.md | n/a
[/CHALLENGE-GATE]
```

---

## 验证方式

```bash
python3 .claude/hooks/challenge-gate/run.py --task "长任务准备交付" --stage delivery --mode H --json
python3 skill-tests/cases/test_challenger_agent.py
python3 skill-tests/cases/test_context_probe_tool.py
```

---

## 维护方式

- 若 Challenger 经常无效触发，优先收窄本 hook 的触发词，不修改 Challenger 角色定义。
- 若 Reviewer 仍发现需求偏离，应在 `memory/candidates/` 生成 hook trigger 候选，补充强制触发场景。
