---
name: diagnose-bug
description: |
  Bug 诊断与修复技能。当生产环境出现 bug、需要分析错误报告、进行根因分析、
  创建回归测试时自动调用。
  Use when given a bug report, traceback, or CT scan. 
  触发词：bug、报错、异常、CT扫描、诊断、traceback、修复。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
context: fork
hooks:
  Stop:
    - hooks:
        - type: prompt
          prompt: |
            Before completing diagnosis, verify ALL of these are done:
            1. Regression test written at tests/regression/test_BUG_<id>.py and PASSES
            2. Full test suite still passes (no regression)
            3. CONTEXT.md §3 (anti-patterns) updated with root cause
            4. PROJECT_MEMORY.md updated
            Check the current state and confirm or identify what's missing. Input: $ARGUMENTS
---

# Bug 诊断技能

## 诊断 SOP

### 1. 读取 CT 报告
```bash
cat projects/<proj>/DIAGNOSIS/BUG_REPORT_<id>.md
# 重点：Traceback（定位代码行）> 触发输入 > 症状描述
```

### 2. 症状解析
```bash
# 从 Traceback 提取模块路径和行号
# 关键词搜索相关 SPEC 和 HUMAN_NOTES
grep -r "<keyword>" modules/*/SPEC.md modules/*/HUMAN_NOTES.md
# 检查 CONTEXT.md §3 是否有相似反模式
grep -A3 "禁止\|反模式" projects/<proj>/CONTEXT.md
```

### 3. 写复现测试（修复前应 FAIL）
```python
# tests/regression/test_BUG_<id>.py
def test_bug_<id>_<short_desc>():
    """复现 BUG-<id>。修复后永久保留为回归防护。"""
    # 构造触发输入
    # 调用触发路径
    # 断言期望行为（修复后的正确结果）
```
```bash
<project_env_cmd> python -m pytest tests/regression/test_BUG_<id>.py -v
# 预期: FAILED ✓（能复现才能修复）
```

### 4. 修复实现
```bash
# 只修改实现代码，不修改测试
# 修复后运行：
<project_env_cmd> python -m pytest tests/regression/test_BUG_<id>.py -v  # PASS
<project_env_cmd> python -m pytest modules/ -v                             # 全部 PASS
<project_env_cmd> python tests/run_all_validators.py                       # 全部 PASS
```

### 5. 知识沉淀（必须完成）
- 更新 `CONTEXT.md §3`（反模式清单）
- 更新 `memory/projects/<proj>/INDEX.md`
- 更新 Bug 报告状态为 🟢 已修复
