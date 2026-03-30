# HOOK: hook-observer
> 触发时机：post-green hook 完成后执行，检测 Hook 触发健康度

---

## 为什么需要 Hook-Observer

Hook 的触发条件是基于关键词匹配的静态规则。随着技术演进（如从 socket 到 asyncio，
从 threading 到 multiprocessing），旧的触发条件会产生漏触发（false negative）。
同时，过于宽泛的触发条件会产生误触发（false positive，噪声）。

Hook-Observer 通过分析 session 执行历史，发现这两类问题并生成改进候选。

---

## 执行步骤

### Step 1: 运行观察脚本
```bash
python3 .claude/hooks/hook-observer/observe.py <PROJECT>
```

### Step 2: 人工阅读输出的候选摘要

脚本会在 `memory/candidates/` 生成 `HOOK_CAND_*.yaml` 文件，并打印摘要。

### Step 3: 漏触发处理
若发现漏触发候选，在下一个涉及相关技术的项目中主动手动执行对应 Hook，
同时在 candidates 文件中追加验证记录。

---

## 检测范围

| 现有 Hook | 当前触发条件 | 已知可能漏触发的技术 |
|-----------|-------------|-------------------|
| network-guard | recv/send/socket | asyncio, aiohttp, websockets, httpx |
| stuck-detector | RED > 2 次（人工判断） | 无自动计数，依赖人工 |
| post-green | 所有测试变绿 | 异步测试框架（pytest-asyncio）可能绕过 |
| context-budget | 完成模块后 | H 模式下批次间切换时机不明确 |

---

## 自动执行脚本
```bash
python3 .claude/hooks/hook-observer/observe.py <PROJECT_NAME>
```

---

## 检查未通过时
不阻塞当前开发流程。输出的候选经人工审核后通过 `/project:skill-review` 提升。
