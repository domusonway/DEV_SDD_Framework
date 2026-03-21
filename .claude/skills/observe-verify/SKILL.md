````markdown
# SKILL: observe-verify
> 任务：为每个模块建立可执行的「观察-验证」自检环路，确保实现与规格客观一致

---

## 为什么需要 Observe & Verify

harness engineering 的核心原则之一：

> **Agent 的主观判断 ≠ 系统的客观验证。**

"测试通过了"不等于"功能正确了"。这是最常见的失败模式：
- Claude 修改了测试断言来让测试通过（违反 MEM_F_C_003）
- 单元测试通过，但集成链路有类型错误（MockSocket 掩盖）
- 功能标记为完成，但 E2E 没有真正运行

Observe & Verify 技能的目标是：在 GREEN 之后，提供一个**客观的、不可绕过的反馈信号**。

---

## 触发时机

1. tdd-cycle VALIDATE 阶段（每模块）
2. 批次完成后、进入下一批次前
3. post-green hook 中（已内置引用）

---

## 三层验证架构

```
Layer 1: 单元验证（最快，<5s）
    ↓ PASS
Layer 2: 接口契约验证（中速，<30s）
    ↓ PASS
Layer 3: 集成/E2E 验证（最慢，按需）
    ↓ PASS
交付就绪
```

---

## Layer 1: 单元验证

```bash
# 运行当前模块测试，要求零失败、零 SKIP
python3 -m pytest tests/test_<module>.py -v --tb=short 2>&1

# 检查实现完整性（不含 pass/return None）
python3 .claude/hooks/observe-verify/check_impl.py modules/<module>/
```

**通过标准：**
- 所有测试 PASS，0 SKIP，0 ERROR
- `check_impl.py` 无裸 `pass` 或 `return None` 报告

---

## Layer 2: 接口契约验证

**目标：** 验证实现的函数签名、输入输出类型与 SPEC 定义完全一致。

```bash
python3 .claude/hooks/observe-verify/check_contract.py \
    --spec modules/<module>/SPEC.md \
    --impl modules/<module>/<impl>.py
```

**检查项：**

| 检查点 | 工具 | 说明 |
|--------|------|------|
| 函数名称 | AST 解析 | 与 SPEC 接口定义一致 |
| 参数名+类型注解 | AST 解析 | 无缺失的类型注解 |
| 返回类型注解 | AST 解析 | **特别检查 bytes vs str** |
| 异常类型 | AST 解析 | 与 SPEC 约定一致 |

**通过标准：** check_contract.py 输出 `✅ CONTRACT OK`

---

## Layer 3: 集成/E2E 验证

**适用场景：** 涉及网络 I/O、跨模块调用、文件 I/O 的模块。

### 网络模块 E2E

```bash
# 使用 socketpair 或真实 loopback 测试
python3 tests/integration/test_<module>_e2e.py

# 必须覆盖：
# - 正常请求/响应链路
# - 连接关闭（b'' 检测）
# - 超时处理
```

### 非网络模块 E2E

```bash
# 用 SPEC 中的示例输入运行，验证输出精确匹配
python3 .claude/hooks/observe-verify/run_spec_examples.py \
    --spec modules/<module>/SPEC.md \
    --impl modules/<module>/<impl>.py
```

---

## 自检命令汇总

每次 VALIDATE 阶段，按顺序执行：

```bash
# 1. 单元测试
python3 -m pytest tests/test_<module>.py -v --tb=short

# 2. 实现完整性
python3 .claude/hooks/observe-verify/check_impl.py modules/<module>/

# 3. 接口契约（如有 SPEC）
python3 .claude/hooks/observe-verify/check_contract.py \
    --spec modules/<module>/SPEC.md \
    --impl modules/<module>/*.py

# 4. 网络代码（如有 recv/send/socket）
python3 .claude/hooks/network-guard/check.py modules/<module>/

# 5. plan-tracker 标记完成
python3 .claude/tools/plan-tracker/tracker.py complete <module>
```

---

## 观察结果记录格式

每次 VALIDATE 完成后，在 session-snapshot CHECKPOINT 中记录：

```
[CHECKPOINT HH:MM]
事件: <module> VALIDATE 完成
观察结果:
  L1 单元: 5/5 PASS ✅
  L2 契约: bytes 返回类型确认 ✅
  L3 E2E: socketpair 测试通过 ✅
  网络检查: 无违规 ✅
发现的问题: （无 / 描述具体问题）
当前状态: <module> → 🟢，PLAN 已更新
[/CHECKPOINT]
```

---

## 验证失败的处理路径

| 失败层级 | 处理方式 |
|---------|---------|
| L1 单元失败 | 回到 GREEN 阶段修复实现，禁止改断言 |
| L2 契约失败 | 修复返回类型/签名与 SPEC 对齐 |
| L3 E2E 失败 | 触发 network-guard 或 diagnose-bug |
| 三层均通过但功能不对 | 重审 SPEC，考虑 SPEC 本身有误 |

---

## 关键原则

- **观察先于判断**：先看工具输出，再得出结论。不要凭感觉说"应该没问题"
- **E2E 是最终裁判**：单元测试全绿不等于功能正确，MockSocket 会掩盖真实错误（MEM_F_I_003）
- **工具输出不截断**：完整读取，不要只看最后几行（MEM_F_C_004 级别的错误经常藏在中间）
- **验证结果写入 CHECKPOINT**：不可只在脑子里过，必须有记录

````

