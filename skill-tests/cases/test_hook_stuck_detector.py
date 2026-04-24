#!/usr/bin/env python3
"""测试 stuck-detector HOOK 文档结构完整性"""
from pathlib import Path
import sys

HOOK_PATH = Path(__file__).parent.parent.parent / ".claude/hooks/stuck-detector/HOOK.md"

def test_hook_exists():
    assert HOOK_PATH.exists()

def test_has_stop_instruction():
    content = HOOK_PATH.read_text()
    assert "停止" in content, "应要求立刻停止修改代码"

def test_has_stuck_record_format():
    content = HOOK_PATH.read_text()
    assert "STUCK" in content and "CHECKPOINT" in content, "应有 STUCK 记录格式"

def test_references_diagnose_bug():
    content = HOOK_PATH.read_text()
    assert "diagnose-bug" in content, "应引用 diagnose-bug skill"

def test_has_common_causes_table():
    content = HOOK_PATH.read_text()
    assert "TypeError" in content, "应包含常见 STUCK 原因"

def test_has_exit_condition():
    content = HOOK_PATH.read_text()
    assert "GREEN" in content or "退出" in content, "应描述退出 STUCK 状态的条件"

if __name__ == "__main__":
    tests = [test_hook_exists, test_has_stop_instruction, test_has_stuck_record_format,
             test_references_diagnose_bug, test_has_common_causes_table,
             test_has_exit_condition]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    sys.exit(failed)
