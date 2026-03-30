# Concurrency 领域记忆 · 索引
> 加载时机：涉及 threading、asyncio、multiprocessing、锁、并发安全时

---

## 快速规则表

| ID | 规则 | 来源 |
|----|------|------|
| MEM_D_CONC_001 | 共享状态用 RLock 而非 Lock，防止同线程递归死锁 | MEM_F_I_007 |
| MEM_D_CONC_002 | C fork+execl → Python subprocess.Popen（多线程安全） | MEM_F_I_005 |
| MEM_D_CONC_003 | asyncio 代码需触发扩展版 network-guard（reader.at_eof() 而非 b''） | HOOK_CAND（待提升）|
| MEM_D_CONC_004 | 每请求一线程模型在高并发下内存压力大，设计阶段需记录此约束 | sdd-tinyhttpd 设计决策 |

---

## 候选规则区

> HOOK_CAND_XXX_001（asyncio 触发扩展）——待第二个项目验证后提升

---

## 跨域关联
- 与 network 领域强关联：网络代码是并发问题的高发区
- H 模式的 sub-agent-isolation 也涉及并发：多个 session 并行写入同一文件的风险
