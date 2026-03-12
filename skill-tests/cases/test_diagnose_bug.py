#!/usr/bin/env python3
"""测试 diagnose-bug SKILL 文档结构完整性"""
from pathlib import Path
import sys

SKILL_PATH = Path(__file__).parent.parent.parent / ".claude/skills/diagnose-bug/SKILL.md"

def test_skill_exists():
    assert SKILL_PATH.exists()

def test_has_stop_instruction():
    content = SKILL_PATH.read_text()
    assert "停止" in content, "应要求停止随机修改"

def test_has_classification():
    content = SKILL_PATH.read_text()
    for err_type in ["TypeError", "ConnectionResetError", "AssertionError"]:
        assert err_type in content, f"缺少错误类型: {err_type}"

def test_has_memory_record_requirement():
    content = SKILL_PATH.read_text()
    assert "memory" in content.lower(), "应要求记录到 memory"

def test_has_rollback_option():
    content = SKILL_PATH.read_text()
    assert "回退" in content or "rollback" in content.lower(), "应提及回退选项"

if __name__ == "__main__":
    tests = [test_skill_exists, test_has_stop_instruction,
             test_has_classification, test_has_memory_record_requirement,
             test_has_rollback_option]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    sys.exit(failed)
