# HOOK: test-sync
> 触发时机：`/project:skill-review` 批准一条候选并执行 promote 后，自动触发

---

## 为什么需要 Test-Sync

每次 Meta-Skill Loop 批准一条新规则写入 SKILL.md，对应的 `skill-tests/cases/test_*.py`
立刻过时——它没有覆盖新规则，但 `run_all.py` 不会报错，因为旧测试仍然全过。

这产生了一个无法被检测的**健康衰减**：框架表面上测试全绿，实际上新规则完全没有测试保护。

Test-Sync 在每次 promote 后自动比对 SKILL.md 规则与测试覆盖，追加缺失的测试桩。

---

## 执行步骤

### Step 1: promote 完成后自动触发
由 `skill-tracker/tracker.py promote` 命令在写入目标文件后自动调用：
```bash
python3 .claude/hooks/test-sync/sync.py --skill <skill_id>
```

### Step 2: 比对规则与测试
脚本解析 SKILL.md 的"禁止行为"和"必须步骤"章节，
与 `skill-tests/cases/test_<skill_id>.py` 中的 `test_*` 函数描述比对。

### Step 3: 追加测试桩
对未覆盖的规则，在测试文件末尾追加 Layer 1 结构测试桩（不调用 API）：
```python
def test_<rule_slug>_exists():
    """AUTO-SYNCED: 覆盖规则 '<rule_text_前40字>'"""
    content = SKILL_PATH.read_text()
    assert "<key_phrase>" in content, \
        "规则已删除或修改，请同步更新测试"
```

### Step 4: 写入 skill-changelog.md
记录"测试已同步"，包含新增的测试函数名列表。

---

## 自动执行脚本
```bash
python3 .claude/hooks/test-sync/sync.py --skill <skill_id>
python3 .claude/hooks/test-sync/sync.py --all  # 全量扫描（初始化时使用）
```

---

## 不自动同步的情况
- Layer 2/3 行为测试（需要人工设计诱导场景）
- Hook 类型的候选（因为 Hook 测试在 `test_hook_*.py` 中，路径规则不同）

这些情况下，sync.py 输出提示但不追加桩，由人工补充。
