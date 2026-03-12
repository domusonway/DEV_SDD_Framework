#!/usr/bin/env python3
"""测试 memory-update SKILL 文档结构完整性"""
from pathlib import Path
import sys

SKILL_PATH = Path(__file__).parent.parent.parent / ".claude/skills/memory-update/SKILL.md"

def test_skill_exists():
    assert SKILL_PATH.exists()

def test_has_attribution_logic():
    content = SKILL_PATH.read_text()
    assert "projects/" in content, "应说明项目记忆路径"
    assert "memory/" in content, "应说明框架记忆路径"

def test_has_promotion_threshold():
    content = SKILL_PATH.read_text()
    assert "3" in content, "应提及 ≥3 个项目验证的升级门槛"

def test_has_memory_file_format():
    content = SKILL_PATH.read_text()
    assert "id:" in content or "severity" in content, "应包含记忆文件格式"

def test_has_cleanup_principle():
    content = SKILL_PATH.read_text()
    assert "精简" in content or "删除" in content, "应强调记忆精简原则"

if __name__ == "__main__":
    tests = [test_skill_exists, test_has_attribution_logic,
             test_has_promotion_threshold, test_has_memory_file_format,
             test_has_cleanup_principle]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    sys.exit(failed)
