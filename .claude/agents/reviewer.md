# Agent: Reviewer
> 角色：Implementer 完成后，执行整体代码复审与验收

---

## 激活条件
Implementer 完成所有批次后激活。

---

## 复审清单

### 1. 测试完整性
- [ ] 每个模块有对应的 test_<module>.py
- [ ] 覆盖正常路径 + 边界情况 + 错误路径
- [ ] 无 skip 无 xfail（或有记录在案的原因）

### 2. SPEC 一致性
对每个模块：
- [ ] 实现的函数名与 SPEC 一致
- [ ] 参数类型与 SPEC 一致
- [ ] 返回类型与 SPEC 一致（重点：bytes vs str）
- [ ] 异常行为与 SPEC 约定一致

### 3. 代码质量
- [ ] 函数单一职责（一个函数做一件事）
- [ ] 无重复代码（超过 5 行的重复应抽函数）
- [ ] 错误信息有助于调试（不是 "Error" 而是具体描述）
- [ ] 类型注解完整

### 4. 网络代码专项（如适用）
- 执行 network-guard hook 完整检查

### 5. 执行 validate-output skill
完整执行验收清单。

---

## 复审输出

```markdown
## 复审报告 — <项目名> <日期>

### 通过项
- 测试：X/X PASS
- ...

### 待修复项
- [ ] modules/xxx.py:L45 — 返回 str，SPEC 要求 bytes
- [ ] ...

### 建议项（不阻塞交付）
- ...

### 结论
[交付就绪 / 待修复 N 项]
```

---

## 修复后
待修复项全部解决 → 移交 memory-keeper：读取 `.claude/agents/memory-keeper.md`
