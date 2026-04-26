# Doc Template BRIEF

- 目标：让 AI 创建文档前先识别文档意图、选择高质量模板、判断归属路径，并校验必填章节。
- 范围：问题分析、架构梳理、项目状态审查、模块验证报告、决策记录、实现简报、规则指引、审查报告八类高频文档。
- 命令：`python3 .claude/tools/doc-template/run.py classify|scaffold|validate ... --json`。
- 模板位置：`docs/templates/`，每个模板包含 frontmatter 元数据和 Markdown 骨架。
- 归属规则：框架文档默认 root `docs/`；项目执行文档默认 `projects/<PROJECT>/docs/`；任务/模块细节默认 `projects/<PROJECT>/docs/sub_docs/`。
- 标准目录：`analysis/`、`architecture/`、`bug/`、`decisions/`、`feature/`、`reports/`、`rules/`、`validation/`。
- 质量门禁：必须包含模板 required_sections；验证报告必须包含入口、上游输入、下游输出、执行命令、证据、风险。
- 语言策略：文档正文默认尽可能使用中文；专业术语、API 名称、代码标识符、命令、路径和英文专有名词保持原文。
- 约束：默认 `scaffold` 只输出建议路径和内容；只有显式 `--write` 才写文件；不得覆盖已有文件，除非显式 `--overwrite`。
- 验收：Layer1 覆盖分类、脚手架路径、模板存在、validate 缺章节告警。
