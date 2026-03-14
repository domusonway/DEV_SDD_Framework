````markdown
# SKILL: tdd-cycle
> 任务：对单个模块执行完整的红绿重构循环

---

## 触发时机
每次开始实现一个模块时读取此 SKILL。

---

## 标准循环（每模块必须完整走完）

```
RED  → GREEN → REFACTOR → VALIDATE → UPDATE-PLAN
```

### RED 阶段
1. 读取 SPEC.md，理解接口契约
2. 写测试文件 `tests/test_<module>.py`
   - **必须覆盖 SPEC 中所有行为规格**（正常路径 + 边界情况 + 错误路径）
   - 测试数量参考：SPEC 有几个"行为规格"小节，至少写几个测试函数
3. **运行测试，确认 FAIL**（不 FAIL = 测试写错，见 MEM_F_I_006）
4. 不写任何实现代码

**RED 阶段完成标志：** 测试文件存在 + 运行结果全部 FAIL

### GREEN 阶段
1. 写实现代码让测试通过
   - **实现必须真正完成 SPEC 描述的功能，不得用硬编码值或空函数骗过测试**
   - 判断标准：把测试输入换一个合法变体，实现仍应返回正确结果
   - 例外：纯 L 模式简单函数可以先写最小实现，REFACTOR 阶段再完善
2. 运行测试，确认全部 PASS
3. 若 RED 超过 2 次 → 触发 `stuck-detector` hook

**GREEN 阶段完成标志：** 所有测试 PASS，且实现函数体不含 `pass`/`return None`/硬编码

### REFACTOR 阶段
1. 在不改变外部行为的前提下清理代码
2. 运行测试，确认仍然全部 PASS
3. 检查并补充：类型注解、文档字符串、错误处理
4. 将遗留的 TODO/FIXME 记录到项目 `memory/INDEX.md` 技术债务区

### VALIDATE 阶段
1. 触发 `post-green` hook
2. 读取 `.claude/skills/validate-output/SKILL.md` 执行验收

### UPDATE-PLAN 阶段（新增，不可跳过）
1. 打开项目 `docs/PLAN.md`
2. 将本模块对应的 `- [ ]` 更新为 `- [x]`，并在行尾注明完成日期
3. 更新项目 `memory/INDEX.md` 中的"模块实现状态"表：
   - 测试状态 → ✅ 验收通过
   - 最后更新 → 今日日期
4. 更新项目 `memory/INDEX.md` 中的"接口快照"表：
   - 将本模块的稳定性标记从 🟡 → 🟢

**UPDATE-PLAN 完成标志：** PLAN.md 中本模块已勾选，memory/INDEX.md 已同步

---

## 网络模块额外检查
写完含 socket/recv/send 的代码后：
- 立即读取 `.claude/hooks/network-guard/HOOK.md` 执行检查
- 不可跳过，不可延后

---

## 状态机

```
[等待任务]
    ↓ 读 SPEC
[RED]  → 测试写错 → 回到 [RED]
         测试未覆盖所有 SPEC 行为 → 补充测试 → 回到 [RED]
    ↓ 确认全部 FAIL
[GREEN] → RED > 2次 → 触发 stuck-detector
          实现用硬编码/pass → 补全实现 → 重新 GREEN
    ↓ 全部 PASS + 实现完整
[REFACTOR]
    ↓ 仍然 PASS
[VALIDATE]
    ↓ 通过
[UPDATE-PLAN]
    ↓ PLAN.md + memory 已更新
[完成]
```

---

## GREEN 阶段实现完整性自查（每次必过）

在进入 REFACTOR 之前，逐项确认：

- [ ] 函数体不含裸 `pass` 或 `return None`（除非 SPEC 明确返回 None）
- [ ] 不含硬编码的测试期望值（如 `return b"HTTP/1.0 200 OK"` 仅为应付断言）
- [ ] 所有 SPEC 中的输入参数都被实际使用
- [ ] 错误路径（ValueError/ConnectionError 等）有真实处理逻辑，不是空 except
- [ ] 用一个**未在测试中出现的合法输入**手动验证，结果符合预期

若有任何一项未通过 → 回到 GREEN 阶段补完实现。

---

## 禁止行为
- 跳过 RED 阶段直接写实现
- RED 阶段测试只写 1-2 个断言，不覆盖 SPEC 全部行为规格
- GREEN 阶段用硬编码值或空函数骗过测试断言
- 在 GREEN 阶段修改测试断言
- 跳过 VALIDATE 直接进入下一模块
- 跳过 UPDATE-PLAN 不更新 PLAN.md 和 memory

````

