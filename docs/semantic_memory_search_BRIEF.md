# Semantic Memory Search BRIEF

- 目标：为 `memory-search` 增加 Bailian embedding 语义检索与本地向量缓存，提升中文/同义任务的经验召回。
- 范围：框架 memory、项目 memory、候选 memory；不读取或打印 `.env` 中的 API Key。
- 默认模型：`text-embedding-v4`，北京地域 100 万 Token 免费额度；LLM 默认 `qwen-flash` 作为后续可选 judge/summary 模型。
- 配置：非密钥默认值集中在根目录 `config.yaml`；`DASHSCOPE_API_KEY` 放 `.env` 或环境变量；`MEMORY_SEARCH_EMBEDDING_MODEL`、`MEMORY_SEARCH_EMBEDDING_DIMENSIONS`、`MEMORY_SEARCH_LLM_MODEL` 可临时覆盖。
- 接口：`memory-search --mode keyword|semantic|hybrid --rebuild-index --vector-db <path> --min-score <float>`。
- 行为：有 Bailian key 时可构建 SQLite 向量库；无 key 或 API 失败时不阻塞，退回关键词检索并给出 warning。
- 验收：Layer1 测试不调用真实 API；semantic/hybrid 输出包含 embedding 配置、vector_db、semantic_hits 或 fallback 信息。
