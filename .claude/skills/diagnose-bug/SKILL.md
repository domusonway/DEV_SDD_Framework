# SKILL: diagnose-bug
> 任务：RED 状态超过 2 次时，系统性诊断并修复 Bug

---

## 触发时机
stuck-detector hook 触发，或人工判断 RED > 2 次时。

---

## 诊断流程

### Step 1: 停止随机改代码
立刻停止。随机修改只会增加噪声，把 RED > 2 变成 RED > 5。

### Step 2: 读取错误信息（完整，不截断）
```bash
python3 -m pytest tests/test_<module>.py -v 2>&1 | head -60
```
记录：
- 错误类型（AssertionError / TypeError / AttributeError / ...）
- 错误位置（文件名 + 行号）
- 期望值 vs 实际值

### Step 3: 分类诊断

#### 类型错误（TypeError / bytes vs str）
→ 检查 SPEC 的 dtype 约定（MEM_F_C_002）
→ 追踪数据从哪里来，在哪里发生类型转换

#### 连接错误（ConnectionResetError / BrokenPipeError）
→ 检查 recv 异常捕获（MEM_F_C_004）
→ 检查 b'' 处理（MEM_F_C_005）

#### 断言失败（AssertionError）
→ 打印实际值：`print(repr(actual))`
→ 检查编码（bytes.decode() 丢失 \r？）
→ 检查空格/换行（\r\n vs \n）

#### 属性错误（AttributeError）
→ 检查接口签名是否与 SPEC 一致
→ 检查返回值结构（dict key 拼写）

### Step 4: 形成假设，单点验证
每次只改一处。改多处 = 无法确定哪个修复有效。

### Step 5: 若 5 次后仍无法修复
1. 在 TODO.md 记录：症状、已尝试方案、假设
2. 回退到最后一个 GREEN 状态
3. 重新审查 SPEC，考虑是否 SPEC 本身有误

---

## 记录要求
Bug 修复后，写入项目 memory：
```
症状：XXX
根因：XXX
修复：XXX
预防：XXX
```
