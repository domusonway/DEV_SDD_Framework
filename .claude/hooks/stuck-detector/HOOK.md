# HOOK: stuck-detector
> 触发时机：RED 状态连续超过 2 次

---

## 触发条件
同一测试文件连续失败超过 2 次（每次修改代码后运行仍然 RED）。

---

## 强制暂停协议

### Step 1: 立刻停止修改代码
不要"再试一次"。更多随机修改会掩盖真正的问题。

### Step 2: 记录当前状态
在 docs/TODO.md 写入：
```
## [STUCK] <时间戳>
症状：<测试名称 + 错误信息摘要>
已尝试：
  - 尝试1：结果
  - 尝试2：结果
当前假设：<下一步想法>
```

### Step 3: 读取 diagnose-bug skill
```
读取 .claude/skills/diagnose-bug/SKILL.md 执行系统性诊断
```

### Step 4: 诊断失败的升级路径
若 diagnose-bug 执行 5 步后仍无法修复：
1. **回退**：`git stash` 或手动回退到最后一个 GREEN 状态
2. **重审 SPEC**：当前 SPEC 是否描述清晰？接口是否合理？
3. **缩小测试范围**：把一个大测试拆成多个小测试，定位最小失败点
4. **添加调试打印**（临时）：`print(repr(actual_value))`

---

## 常见 STUCK 原因与快速定位

| 症状 | 快速检查 |
|------|---------|
| TypeError: bytes/str | SPEC dtype 约定，检查返回值类型 |
| ConnectionResetError | recv 异常捕获，MEM_F_C_004 |
| AssertionError: 值不匹配 | print(repr()) 看实际值，\r\n vs \n |
| AttributeError | 函数签名与调用方不一致 |
| 测试直接 PASS（无实现）| 测试逻辑有误，检查断言条件 |
| ImportError | 模块路径/包结构问题 |

---

## 退出 STUCK 状态
完成 diagnose-bug 流程后，确认问题根因，写一行修复，运行测试。
成功 GREEN → 从 stuck-detector 退出，继续正常 tdd-cycle。
