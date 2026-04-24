````markdown
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
- 若有 SKIP：必须有记录在案的原因（session 快照或项目 memory）
- **测试数量合理性：每个模块的测试函数数 ≥ SPEC 中行为规格小节数**

### 2. 实现完整性检查（新增，对应问题4）

对每个模块的实现文件执行：
```bash
# 检查是否有未实现的占位符
grep -rn "pass$\|return None\|raise NotImplementedError\|TODO.*implement" modules/
```

逐模块确认：
- [ ] 函数体不含裸 `pass`（除非是抽象接口）
- [ ] 不含仅为通过测试的硬编码返回值
- [ ] 所有 SPEC 中的行为规格（正常路径 + 边界 + 错误路径）均有对应实现
- [ ] 用一个测试文件中未出现的合法输入，手动验证返回值符合 SPEC

### 3. 接口契约验证
对每个模块：
- [ ] 返回类型与 SPEC 一致（bytes/str/int/dict）
- [ ] 异常处理与 SPEC 约定一致
- [ ] 函数签名与 SPEC 接口表一致（重点：bytes vs str）

### 4. 网络代码专项检查（如适用）
运行 `.claude/hooks/network-guard/HOOK.md` 检查清单：
- [ ] recv 异常捕获正确（MEM_F_C_004）
- [ ] b'' 连接关闭检查（MEM_F_C_005）
- [ ] sendall 而非 send（防止部分发送）

### 5. 校验器自测
```bash
for validator in tests/validators/validate_*.py; do
    python3 "$validator" --self-test
done
```
- [ ] 所有校验器用参考输出自测通过（MEM_F_C_001）

### 6. 集成/E2E 测试（如有）
```bash
python3 tests/e2e_test.py
```
- [ ] 完整请求/响应链路通过
- [ ] 错误场景（404, 500）正确处理

### 7. 代码质量扫描
```bash
python3 -m py_compile modules/**/*.py   # 语法检查
grep -rn "except Exception:" modules/  # 检查宽泛异常捕获
grep -rn "TODO\|FIXME\|HACK" modules/  # 遗留标记（记录到 memory 技术债务）
```

### 8. PLAN.md 同步检查（新增）
```bash
grep -c "\- \[ \]" docs/PLAN.md  # 应为 0（无未勾选项）
```
- [ ] docs/PLAN.md 中所有模块已勾选（`[x]`）
- [ ] memory/INDEX.md 的"模块实现状态"全部为 ✅
- [ ] memory/INDEX.md 的"接口快照"全部为 🟢

---

## 验收结果输出
```
验收报告
========
测试：X/X PASS，0 SKIP，0 ERROR
实现完整性：✅ / ❌ [细节，如：modules/xxx.py 存在裸 pass]
接口契约：✅ / ❌ [细节]
网络检查：✅ / ❌ / N/A
校验器自测：✅ / ❌ / N/A
E2E：✅ / ❌ / N/A
代码质量：✅ / ⚠️ [细节]
PLAN同步：✅ / ❌ [待勾选模块列表]

结论：[交付就绪 / 待修复: XXX]
```

---

## 实现完整性判定标准（补充说明）

**不完整的典型特征：**
```python
# ❌ 骗过测试的硬编码
def build_response(status_code, body, content_type="text/html"):
    return b"HTTP/1.0 200 OK\r\n\r\n" + body   # status_code 未被使用

# ❌ 骗过测试的最小返回
def route(path, htdocs_root):
    return "static"   # 所有路径都返回 static，测试恰好没覆盖 cgi 路径

# ❌ 空函数体
def parse_request(conn):
    pass
```

**完整实现的特征：**
```python
# ✅ 真实实现：所有参数都被使用，所有分支都有逻辑
def build_response(status_code: int, body: bytes,
                   content_type: str = "text/html; charset=utf-8",
                   extra_headers: dict = None) -> bytes:
    status_text = {200: "OK", 404: "Not Found", 500: "Internal Server Error"}.get(
        status_code, "Unknown")
    headers = [
        f"HTTP/1.0 {status_code} {status_text}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body)}",
    ]
    if extra_headers:
        headers.extend(f"{k}: {v}" for k, v in extra_headers.items())
    return "\r\n".join(headers).encode() + b"\r\n\r\n" + body
```

````
