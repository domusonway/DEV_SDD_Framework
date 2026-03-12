#!/usr/bin/env python3
"""测试 tdd-cycle SKILL 文档结构完整性"""
from pathlib import Path
import sys

SKILL_PATH = Path(__file__).parent.parent.parent / ".claude/skills/tdd-cycle/SKILL.md"

def test_skill_exists():
    assert SKILL_PATH.exists(), f"不存在: {SKILL_PATH}"

def test_has_red_green_refactor():
    content = SKILL_PATH.read_text()
    for phase in ["RED", "GREEN", "REFACTOR", "VALIDATE"]:
        assert phase in content, f"缺少阶段: {phase}"

def test_has_network_hook_mention():
    content = SKILL_PATH.read_text()
    assert "network-guard" in content, "应提及 network-guard hook"

def test_has_stuck_trigger():
    content = SKILL_PATH.read_text()
    assert "stuck-detector" in content, "应提及 stuck-detector 触发条件"

def test_has_forbidden_behaviors():
    content = SKILL_PATH.read_text()
    assert "禁止" in content, "应明确禁止行为"

if __name__ == "__main__":
    tests = [test_skill_exists, test_has_red_green_refactor,
             test_has_network_hook_mention, test_has_stuck_trigger,
             test_has_forbidden_behaviors]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    sys.exit(failed)
