# SKILL: doc-template
> 任务：创建文档前识别意图、选择模板、确定路径并执行质量校验。

---

## 触发时机

用户要求写文档、报告、分析、审查、规则、方案、模块验证记录时触发。

---

## 执行步骤

1. 使用 helper 识别文档类型：

```bash
python3 .claude/tools/doc-template/run.py classify "<用户任务描述>" --json
```

2. 使用匹配模板生成骨架或建议路径：

```bash
python3 .claude/tools/doc-template/run.py scaffold <template-id> --project <PROJECT> --module <MODULE> --json
```

3. 写入或修改文档后执行质量校验：

```bash
python3 .claude/tools/doc-template/run.py validate <doc-path> --template <template-id> --json
```

---

## 强制规则

1. 创建文档前必须判断文档类型和归属路径。
2. 项目执行文档不得写到 root `docs/`。
3. 任务/模块细节默认写入 `projects/<PROJECT>/docs/sub_docs/`。
4. 输出必须包含模板 required_sections。
5. 若意图不明确，只问一个问题确认类型；若用户目标明确，直接选模板。
6. 写完后报告模板匹配结果和质量校验结果。
7. 正常开发中凡是需要创建文档，必须先输出 `[DOC-TEMPLATE]` 块，明确命中模板和目标路径。
8. 文档正文默认尽可能使用中文；专业术语、API 名称、代码标识符、命令、文件路径、协议字段和英文专有名词保持原文。

---

## 输出块

创建文档前必须输出：

```markdown
[DOC-TEMPLATE]
intent: <文档意图>
template_id: <模板ID>
confidence: <high|medium|low>
target_path: <建议写入路径>
language: zh-CN default, preserve technical terms
validation_required: true
[/DOC-TEMPLATE]
```

若 `confidence: low`，只问一个澄清问题，不直接创建文档。

---

## 标准目录

| Directory | Template IDs |
|---|---|
| `analysis/` | `problem-analysis` |
| `architecture/` | `architecture-overview` |
| `bug/` | `problem-analysis` |
| `decisions/` | `decision-record` |
| `feature/` | `implementation-brief` |
| `reports/` | `project-status-review`, `review-report` |
| `rules/` | `rule-guide` |
| `validation/` | `module-validation-report` |
