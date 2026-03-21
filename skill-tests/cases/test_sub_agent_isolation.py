#!/usr/bin/env python3
"""测试 sub-agent-isolation SKILL 文档结构完整性"""
from pathlib import Path
import sys

SKILL_PATH = Path(__file__).parent.parent.parent / ".claude/skills/sub-agent-isolation/SKILL.md"


def test_skill_exists():
    assert SKILL_PATH.exists(), f"SKILL.md 不存在: {SKILL_PATH}"


def test_has_context_firewall_concept():
    content = SKILL_PATH.read_text()
    assert "Context Firewall" in content or "隔离" in content, \
        "应包含 Context Firewall 概念"


def test_has_phase_separation():
    content = SKILL_PATH.read_text()
    for phase in ["Initializer", "Implementer"]:
        assert phase in content, f"应定义 {phase} 对话阶段"


def test_has_filesystem_as_boundary():
    content = SKILL_PATH.read_text()
    assert "文件系统" in content or "filesystem" in content.lower(), \
        "应说明文件系统作为隔离边界"


def test_has_init_sh_pattern():
    content = SKILL_PATH.read_text()
    assert "init.sh" in content, "应包含 init.sh 环境验证模式"


def test_has_handoff_integration():
    content = SKILL_PATH.read_text()
    assert "HANDOFF" in content, "应集成 HANDOFF.json 交接机制"


def test_has_git_as_state_store():
    content = SKILL_PATH.read_text()
    assert "git" in content, "应将 git 作为可靠的状态存储"


def test_has_compression_principle():
    content = SKILL_PATH.read_text()
    assert "压缩" in content or "compact" in content.lower(), \
        "应说明子 agent 结果需压缩后传递给父 agent"


def test_has_what_not_to_read():
    content = SKILL_PATH.read_text()
    # 应明确说明父 agent 不需要读哪些信息
    assert "不需要" in content or "不要读" in content or "❌" in content, \
        "应明确说明父 agent 不应读入的信息（避免 context 污染）"


if __name__ == "__main__":
    tests = [
        test_skill_exists,
        test_has_context_firewall_concept,
        test_has_phase_separation,
        test_has_filesystem_as_boundary,
        test_has_init_sh_pattern,
        test_has_handoff_integration,
        test_has_git_as_state_store,
        test_has_compression_principle,
        test_has_what_not_to_read,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    sys.exit(failed)
