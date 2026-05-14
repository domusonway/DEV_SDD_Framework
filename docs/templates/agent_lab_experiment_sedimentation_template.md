# Agent Lab 实验沉淀模板

> 用途：每轮 `agent_lab_space/` 实验结束后复制本模板，保存到对应实验目录或报告目录。  
> 目标：让实验过程、指标、失败样本、资产候选和产品化决策可阅读、可复验、可沉淀。

## Frontmatter

```yaml
---
experiment_id: E00_baseline
title: <实验标题>
status: planned | running | completed | blocked | discarded
owner: <执行人或 agent>
created_at: YYYY-MM-DD HH:MM
updated_at: YYYY-MM-DD HH:MM
modules:
  - runtime
  - evaluation
chain:
  - evaluation
  - runtime
dataset_manifest: agent_lab_space/datasets/manifests/<manifest>.json
run_root: agent_lab_space/runs/<timestamp>/
asset_decision: discard | keep_in_lab | promote_candidate
---
```

## 1. 实验声明

| 项 | 内容 |
|---|---|
| 实验问题 | <本轮要验证什么问题> |
| 第一性原理 | <为什么这个问题对产品化质检重要> |
| 假设 | <如果调整 X，则指标 Y 应改善，因为 Z> |
| 实验链路 | <runtime / runtime + intelligence / studio + runtime ...> |
| 主要变量 | <本轮唯一或主要调整变量> |
| 控制变量 | <保持不变的模型、样本、prompt、skill、memory 等> |
| 成功标准 | <量化指标和门禁> |
| 停止条件 | <何时停止或回滚本实验> |

## 2. 变量与对照组

| 项 | 内容 |
|---|---|
| Baseline | <baseline 配置、commit/hash、报告路径> |
| Variant | <本轮实验 variant 配置、路径、差异> |
| 单变量说明 | <本轮只改变了什么；若多变量，解释原因和归因方式> |
| 随机性控制 | <seed、repeat 次数、provider temperature 等> |
| 反向验证 | <good case、防 FP、历史 blocker case 的验证方式> |

## 3. 样本与数据

| 项 | 内容 |
|---|---|
| 数据集 | <GoodsAD / case lake / 自定义样本> |
| 样本规模 | <random sample / remaining / full> |
| 分层策略 | <easy / medium / hard / defect type / product type> |
| Ground truth 来源 | <expected labels / boxes / oracle 文件> |
| 样本丰富性说明 | <覆盖哪些产品、缺陷、位置、难度> |
| 图片有效性 | <是否过滤不可解码图片、placeholder、ASCII jpg> |
| 数据污染检查 | <是否去除 expected labels、expected boxes、可推断答案的 case id> |

## 4. 实验配置

| 项 | 内容 |
|---|---|
| 模型池 | <model_pool 配置或模型列表> |
| Provider | <real provider / oracle / mock> |
| Routing reason | <为什么选择该模型或触发 failover> |
| Prompt/Skill 版本 | <路径、hash 或说明> |
| Memory/Experience 版本 | <路径、release id 或说明> |
| Runtime policy | <关键策略> |
| Audit policy | <如适用> |
| 成本/延迟 SLA | <token、cost、avg/p95 latency> |

## 5. 执行命令

```bash
# small batch
<command>

# cross validation
<command>

# productization gate
<command>

# regression guard
<command>
```

## 6. 结果摘要

| 指标 | Baseline | Variant | Delta | 是否通过 |
|---|---:|---:|---:|---|
| pass_rate | | | | |
| hard_pass_rate | | | | |
| false_positive_rate | | | | |
| false_negative_rate | | | | |
| critical_miss_rate | | | | |
| review_rate | | | | |
| avg_latency_ms | | | | |
| p95_latency_ms | | | | |
| avg_cost | | | | |
| token_usage_avg | | | | |
| fallback_rate | | | | |

## 7. 分层分析

| 分层 | 样本数 | pass_rate | FP | FN | critical_miss | latency | 结论 |
|---|---:|---:|---:|---:|---:|---:|---|
| easy | | | | | | | |
| medium | | | | | | | |
| hard | | | | | | | |
| good | | | | | | | |
| defect | | | | | | | |

## 8. 失败样本复盘

| case_id | 难度 | 期望 | 预测 | 失败原因 | 根因判断 | 下一步 |
|---|---|---|---|---|---|---|
| | | | | | | |

复盘要求：

- 明确是数据问题、prompt/skill 问题、runtime 链路问题、memory 注入问题、模型能力问题，还是 scoring/taxonomy 问题。
- 禁止通过修改 ground truth、降低 gate、跳过 hard case 来制造通过。
- 若需要真实 provider，oracle 只能作为工程链路对照，不能作为产品化准确率结论。

## 9. 模型池与成本分析

| model | provider | routing_reason | cases | pass_rate | critical_miss | avg_latency_ms | p95_latency_ms | avg_cost | fallback_rate | 结论 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| | | | | | | | | | | |

## 10. 资产候选

| 资产类型 | 路径/名称 | 价值 | 风险 | 决策 |
|---|---|---|---|---|
| prompt_variant | | | | discard / keep_in_lab / promote_candidate |
| skill_candidate | | | | discard / keep_in_lab / promote_candidate |
| memory_candidate | | | | discard / keep_in_lab / promote_candidate |
| agent_variant | | | | discard / keep_in_lab / promote_candidate |
| model_routing_rule | | | | discard / keep_in_lab / promote_candidate |

## 11. 产品化判断

| Gate | 结果 | 证据 |
|---|---|---|
| 工程链路 | PASS / FAIL | <trace/contract/fallback evidence> |
| 准确率 | PASS / FAIL | <case lake summary> |
| 风险 | PASS / FAIL | <FP/FN/critical miss> |
| 成本 | PASS / FAIL | <cost/token> |
| 延迟 | PASS / FAIL | <avg/p95 latency> |
| 可维护性 | PASS / FAIL | <复杂度、回滚、资产边界> |
| 审计 | PASS / FAIL / N/A | <audit report> |

结论：`not_ready | keep_experimenting | ready_for_productization_candidate`

## 12. 晋升与回滚计划

| 项 | 内容 |
|---|---|
| Promote 前置 | <BRIEF/SPEC、测试、review、gate> |
| 正式落点 | <正式 skill/memory/agent/model routing rule 路径> |
| 回滚方式 | <如何撤回正式资产> |
| 兼容影响 | <对 runtime/evaluation/studio/audit 的影响> |

## 13. 沉淀决策

```markdown
[EXPERIMENT-SEDIMENTATION]
experiment_id: <E00_xxx>
decision: discard | keep_in_lab | promote_candidate
reason: <一句话说明为什么>
assets:
  - <路径或无>
memory_action: no_sedimentation | project_memory | framework_candidate
follow_up:
  - <下一轮实验或产品化任务>
[/EXPERIMENT-SEDIMENTATION]
```

## 14. 复验清单

- [ ] Small batch 命令可复跑。
- [ ] Cross validation 命令可复跑。
- [ ] Real provider gate 或明确的环境阻塞已记录。
- [ ] 输出报告和原始结果保存到 `agent_lab_space/`。
- [ ] 资产候选没有污染正式 `modules/core`、默认 skill、默认 memory。
- [ ] Ground truth、hard case、good case 和 adapter contract 未被放宽或跳过。
- [ ] 若 promote，需要补 BRIEF/SPEC、测试、产品化 gate 和 memory 更新。
