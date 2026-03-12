# SKILL: tdd-cycle
> 任务：对单个模块执行完整的红绿重构循环

---

## 触发时机
每次开始实现一个模块时读取此 SKILL。

---

## 标准循环（每模块必须完整走完）

```
RED  → GREEN → REFACTOR → VALIDATE
```

### RED 阶段
1. 读取 SPEC.md，理解接口契约
2. 写测试文件 `tests/test_<module>.py`
3. **运行测试，确认 FAIL**（不 FAIL = 测试写错，见 MEM_F_I_006）
4. 不写任何实现代码

### GREEN 阶段
1. 写最小实现让测试通过（可以丑，不求完美）
2. 运行测试，确认全部 PASS
3. 若 RED 超过 2 次 → 触发 `stuck-detector` hook

### REFACTOR 阶段
1. 在不改变外部行为的前提下清理代码
2. 运行测试，确认仍然全部 PASS
3. 检查：类型注解、文档字符串、错误处理

### VALIDATE 阶段
1. 触发 `post-green` hook
2. 读取 `.claude/skills/validate-output/SKILL.md` 执行验收

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
    ↓ 确认 FAIL
[GREEN] → RED > 2次 → 触发 stuck-detector
    ↓ 全部 PASS
[REFACTOR]
    ↓ 仍然 PASS
[VALIDATE]
    ↓ 通过
[完成]
```

---

## 禁止行为
- 跳过 RED 阶段直接写实现
- 在 GREEN 阶段修改测试断言
- 跳过 VALIDATE 直接进入下一模块
