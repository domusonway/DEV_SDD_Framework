# SKILL: prompt-policy
> 任务：按用户任务大类自动注入质量约束提示词，提升审查、分析、文档和规划类任务的输出标准

---

## 触发时机

启动协议 Step 2.5 的 context-probe 之后立即执行。读取用户任务描述，识别大类并输出 `[PROMPT-POLICY]` 块。

---

## 设计原则

1. 只做大类区分，不做过细意图分类。
2. 注入的是质量约束，不替代用户需求、不扩大任务范围。
3. 约束必须可执行、可检查、低噪声。
4. 多个大类同时命中时最多注入 3 组约束，按风险优先。
5. 若用户明确要求轻量回答，只保留最高优先级约束。

---

## 任务大类识别

| 大类 | 关键词/场景 | 注入目标 |
|---|---|---|
| `review_evaluate_analyze` | 审查、评估、分析、确认、风险、局限、是否全面准确 | 提高判断质量，要求全面、准确、清晰、指标规范 |
| `doc_creation` | 创建文档、写文档、记录、沉淀、报告、方案文档 | 保证文档位置、格式、真相源和维护边界正确 |
| `planning_parallel` | 规划、计划、plan.json、PLAN.md、多模块、并行、依赖、lane | 要求显式依赖、共享资产、冲突、owner、merge gate |
| `memory_review` | 经验沉淀、memory、candidate、人工审核、promote、规则提升 | 要求证据、作用域、风险、生命周期、回滚边界 |
| `implementation_fix` | 实现、修复、重构、测试通过、性能达标 | 要求 SPEC/TDD、最小正确改动、验证和沉淀决策 |

---

## 注入提示词

### review_evaluate_analyze

```text
质量约束：确认检查内容全面、准确、清晰；每一个指标或判断维度必须定义规范；结论必须区分已验证事实、推断和残余风险；若证据不足，明确说明缺口，不得过度确认。
```

### doc_creation

```text
质量约束：创建或修改文档前先使用 doc-template 判断文档类型与归属位置，并输出 `[DOC-TEMPLATE]` 块；框架级文档放 root docs/，项目执行文档放 projects/<PROJECT>/docs/，任务细节放 docs/sub_docs/；文档正文默认尽可能使用中文，专业术语/API/代码/命令/路径保留原文；保持既有格式和命名风格；不得把生成视图当作真相源；写完后运行 doc-template validate。
```

辅助命令：

```bash
python3 .claude/tools/doc-template/run.py classify "<用户任务描述>" --json
python3 .claude/tools/doc-template/run.py scaffold <template-id> --project <PROJECT> --module <MODULE> --json
python3 .claude/tools/doc-template/run.py validate <doc-path> --template <template-id> --json
```

### planning_parallel

```text
质量约束：规划必须显式列出 deps/blocked_by、parallel group、owner、shared artifacts、writes/reads、handoff artifacts 和 merge gate；必须说明哪些任务可并行、哪些必须串行、哪里可能互相等待或写入冲突。
```

### memory_review

```text
质量约束：经验沉淀和候选审核必须包含 evidence、scope、confidence、risk、status、validated_projects 和 rollback/deprecate 边界；不得把单项目低置信经验直接提升为框架规则。
```

### implementation_fix

```text
质量约束：实现/修复/重构必须遵循 SPEC -> tests -> implementation；优先最小正确改动；测试失败只改实现；完成后运行相关验证，并输出 Sedimentation Decision。
```

---

## 输出格式

必须输出：

```markdown
[PROMPT-POLICY]
matched: <大类，多个用逗号分隔>
injected:
- <注入的质量约束 1>
- <注入的质量约束 2>
[/PROMPT-POLICY]
```

若没有命中：

```markdown
[PROMPT-POLICY]
matched: none
injected: none
[/PROMPT-POLICY]
```

---

## 优先级

当命中超过 3 类时，按以下顺序保留：

1. `implementation_fix`
2. `planning_parallel`
3. `memory_review`
4. `doc_creation`
5. `review_evaluate_analyze`

---

## 禁止行为

1. 不得把提示词策略当作用户新需求扩大范围。
2. 不得输出超过 3 组注入约束，避免上下文污染。
3. 不得隐藏注入内容，必须用 `[PROMPT-POLICY]` 显式展示。
4. 不得用提示词策略绕过 SPEC、TDD、memory 或权限规则。
