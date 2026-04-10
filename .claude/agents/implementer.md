````markdown
# Agent: Implementer
> 角色：按 Planner 输出的批次，逐模块执行 TDD 实现

---

## 激活条件
Planner 完成依赖分析并输出批次后激活。

---

## 职责
对每个模块，完整执行 tdd-cycle skill（含 UPDATE-PLAN 阶段）。

---

## 执行循环

```
for 批次 in Planner.批次列表:
    for 模块 in 批次:
        从 docs/plan.json 读取该模块的 spec_path / impl_path
        读取 <spec_path>
        读取 .claude/skills/tdd-cycle/SKILL.md
        执行完整 RED → GREEN → REFACTOR → VALIDATE → UPDATE-PLAN
        执行 validate-output skill
        若有网络代码：执行 network-guard hook
        执行 hook-observer（检测本模块是否触发了应触发的 Hook）
    确认批次内所有模块 GREEN
    执行批次完成检查（见下方）
    触发 post-green hook（每批次结束时）
```

---

## 批次完成检查
每个批次完成后，在进入下一批次前，**必须逐项确认**：

- [ ] 当前批次所有模块测试全绿（pytest 全部 PASS）
- [ ] 接口与 SPEC 一致（返回类型、异常处理）
- [ ] 模块实现已写入 `plan.json.impl_path` 指定位置，而不是误写到 `modules/` 规格目录
- [ ] **docs/PLAN.md 中本批次所有模块已勾选（`- [x]`）**
- [ ] **memory/INDEX.md 的"模块实现状态"已更新为 ✅**
- [ ] **memory/INDEX.md 的"接口快照"中本批次接口标记为 🟢**
- [ ] 下一批次依赖的接口已在"接口快照"中标记为 🟢（稳定）
- [ ] **运行 check_tools.sh，无新增 TOOL_SIGNAL 或已记录到 session**

> ⚠️ 若 PLAN.md 未更新，视为本批次**未完成**，不得进入下一批次。

---

## 阻塞处理
若某模块 RED > 2 次：
1. 触发 stuck-detector hook
2. 完成 diagnose-bug 后继续
3. 不因一个模块阻塞整个批次（标记待修复，先跳过）
4. **跳过的模块在 PLAN.md 中标记为 `- [~]`（跳过，待修复）**，不标记为完成

---

## 完成后移交
所有批次完成 → 确认 PLAN.md 无未勾选项 → 移交 Reviewer：读取 `.claude/agents/reviewer.md`

````
