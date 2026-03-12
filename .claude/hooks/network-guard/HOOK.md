# HOOK: network-guard
> 触发时机：写完任何含 recv/send/socket 的代码后，立即执行

---

## 检查清单（逐项确认，不可跳过）

### ✅ recv 异常捕获
```python
# 要求：精确捕获三类，不用 except Exception
except (socket.timeout, ConnectionResetError, OSError):
```
- [ ] 所有 recv 调用在 try 块内
- [ ] except 子句只捕获上述三类（+ 可选的 Exception 用于日志）
- [ ] 无裸 `except:` 或 `except Exception: pass`

### ✅ b'' 连接关闭检查
```python
data = conn.recv(4096)
if not data:   # 必须有
    break
```
- [ ] 每个 recv 调用后都有 `if not data: break`（或等价检查）

### ✅ sendall 而非 send
- [ ] 所有发送操作使用 `conn.sendall()` 不用 `conn.send()`

### ✅ socket 关闭
- [ ] socket 在 finally 块或 with 语句中关闭
- [ ] 服务器 socket 设置了 `SO_REUSEADDR`

---

## 自动执行脚本
```bash
python3 .claude/hooks/network-guard/check.py <file_or_dir>
```

---

## 检查未通过时
停止继续编写代码，先修复检查项，再运行测试。
网络代码的隐性 Bug 在单元测试中不会显现，在 E2E 才爆。
