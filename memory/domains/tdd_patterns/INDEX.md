# TDD Patterns 领域记忆 · 索引
> 加载时机：涉及 TDD 流程问题、测试设计、RED/GREEN 阶段失败时

---

## 快速规则表

| ID | 规则 | 来源 |
|----|------|------|
| MEM_D_TDD_001 | RED 阶段测试直接 PASS = 测试逻辑有误，必须修复测试而非进入 GREEN | framework |
| MEM_D_TDD_002 | 测试数量 ≥ SPEC 行为规格小节数，少于此数视为覆盖不足 | framework |
| MEM_D_TDD_003 | GREEN 阶段禁止硬编码：函数体必须实际使用所有输入参数 | framework |
| MEM_D_TDD_004 | UPDATE-PLAN 是 tdd-cycle 的必须步骤，不可跳过 | framework |

---

## 候选规则区（来自 candidates/，待提升）

> 此区域由 meta-skill-agent 自动维护，候选通过审核后移入上方正式表格

（暂无）

---

## 跨域关联
- 与 type_safety 领域重叠：bytes/str 错误常在 GREEN 阶段的硬编码中被掩盖
- 与 network 领域重叠：MockSocket 会掩盖接口契约错误（见 MEM_F_I_003）
