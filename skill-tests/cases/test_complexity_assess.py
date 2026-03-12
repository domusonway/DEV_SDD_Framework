#!/usr/bin/env python3
"""测试 complexity-assess SKILL 文档结构完整性"""
from pathlib import Path
import sys

SKILL_PATH = Path(__file__).parent.parent.parent / ".claude/skills/complexity-assess/SKILL.md"

def test_skill_exists():
    assert SKILL_PATH.exists(), f"SKILL.md 不存在: {SKILL_PATH}"

def test_skill_has_required_sections():
    content = SKILL_PATH.read_text()
    required = ["触发时机", "评分维度", "模式判定", "执行步骤", "输出格式"]
    missing = [s for s in required if s not in content]
    assert not missing, f"缺少必要章节: {missing}"

def test_skill_has_three_modes():
    content = SKILL_PATH.read_text()
    for mode in ["L 轻量", "M 标准", "H 完整"]:
        assert mode in content, f"缺少模式: {mode}"

def test_skill_references_tdd_cycle():
    content = SKILL_PATH.read_text()
    assert "tdd-cycle" in content, "应引用 tdd-cycle skill"

if __name__ == "__main__":
    tests = [test_skill_exists, test_skill_has_required_sections,
             test_skill_has_three_modes, test_skill_references_tdd_cycle]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    sys.exit(failed)
