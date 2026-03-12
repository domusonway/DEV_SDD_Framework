#!/usr/bin/env python3
"""测试 validate-output SKILL 文档结构完整性"""
from pathlib import Path
import sys

SKILL_PATH = Path(__file__).parent.parent.parent / ".claude/skills/validate-output/SKILL.md"

def test_skill_exists():
    assert SKILL_PATH.exists()

def test_has_checklist():
    content = SKILL_PATH.read_text()
    assert "- [ ]" in content, "应包含检查清单格式"

def test_has_network_check():
    content = SKILL_PATH.read_text()
    assert "network-guard" in content, "应包含网络代码检查"

def test_has_validator_selftest():
    content = SKILL_PATH.read_text()
    assert "自测" in content or "self-test" in content.lower(), "应要求校验器自测"

def test_has_output_format():
    content = SKILL_PATH.read_text()
    assert "验收报告" in content or "结论" in content, "应有输出格式定义"

if __name__ == "__main__":
    tests = [test_skill_exists, test_has_checklist, test_has_network_check,
             test_has_validator_selftest, test_has_output_format]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    sys.exit(failed)
