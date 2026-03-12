# SKILL: validate-output
> 任务：所有测试 GREEN 后，执行最终交付验收

---

## 触发时机
post-green hook 触发后，或人工在所有测试通过后执行。

---

## 验收清单

### 1. 测试覆盖率检查
```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
- 所有测试 PASS，零 SKIP，零 ERROR
- 若有 SKIP：必须有记录在案的原因（TODO.md）

### 2. 接口契约验证
对每个模块：
- [ ] 返回类型与 SPEC 一致（bytes/str/int/dict）
- [ ] 异常处理与 SPEC 约定一致
- [ ] 函数签名与 SPEC 接口表一致

### 3. 网络代码专项检查（如适用）
运行 `.claude/hooks/network-guard/HOOK.md` 检查清单：
- [ ] recv 异常捕获正确（MEM_F_C_004）
- [ ] b'' 连接关闭检查（MEM_F_C_005）
- [ ] sendall 而非 send（防止部分发送）

### 4. 校验器自测
```bash
# 对每个校验器运行自测
for validator in tests/validators/validate_*.py; do
    python3 "$validator" --self-test
done
```
- [ ] 所有校验器用参考输出自测通过（MEM_F_C_001）

### 5. 集成/E2E 测试（如有）
```bash
python3 tests/e2e_test.py
```
- [ ] 完整请求/响应链路通过
- [ ] 错误场景（404, 500）正确处理

### 6. 代码质量扫描
```bash
python3 -m py_compile modules/**/*.py   # 语法检查
grep -rn "except Exception:" modules/  # 检查宽泛异常捕获
grep -rn "TODO\|FIXME\|HACK" modules/  # 遗留标记
```

---

## 验收结果输出
```
验收报告
========
测试：X/X PASS，0 SKIP，0 ERROR
接口契约：✅ / ❌ [细节]
网络检查：✅ / ❌ [细节]
校验器自测：✅ / ❌ [细节]
E2E：✅ / ❌ / N/A
代码质量：✅ / ⚠️ [细节]

结论：[交付就绪 / 待修复: XXX]
```
