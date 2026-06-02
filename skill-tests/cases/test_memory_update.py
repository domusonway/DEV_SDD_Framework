#!/usr/bin/env python3
"""测试 memory-update SKILL 文档结构完整性"""
from pathlib import Path
import sys

SKILL_PATH = Path(__file__).parent.parent.parent / ".claude/skills/memory-update/SKILL.md"
FRAMEWORK_ENTRY = Path(__file__).parent.parent.parent / "AGENTS.md"
SESSION_HOOK = Path(__file__).parent.parent.parent / ".claude/hooks/session-snapshot/HOOK.md"

def test_skill_exists():
    assert SKILL_PATH.exists()

def test_has_attribution_logic():
    content = SKILL_PATH.read_text()
    assert "projects/" in content, "应说明项目记忆路径"
    assert "memory/" in content, "应说明框架记忆路径"

def test_has_asset_owner_project_root_guard():
    content = SKILL_PATH.read_text(encoding="utf-8")
    assert "ASSET_PROJECT_ROOT" in content, "应先判定资产所属项目根"
    assert "sibling 子仓库" in content, "应覆盖 workspace sibling 子仓库归属"
    assert "不得因为索引缺失" in content, "缺少 memory/INDEX.md 时不得退回写入当前激活项目"
    assert "agent_lab_space" in content and "agentplatform/memory" in content, "应包含 lab-only 规则误写防回归示例"

def test_framework_entry_and_session_hook_share_asset_owner_boundary():
    entry = FRAMEWORK_ENTRY.read_text(encoding="utf-8")
    hook = SESSION_HOOK.read_text(encoding="utf-8")
    for content in (entry, hook):
        assert "资产所属项目优先" in content, "入口和 session hook 都应声明资产所属项目优先"
        assert "当前激活 `PROJECT_PATH` 只作为默认" in content, "不得让 active PROJECT_PATH 覆盖 sibling 资产归属"

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
    tests = [test_skill_exists, test_has_attribution_logic, test_has_asset_owner_project_root_guard,
             test_framework_entry_and_session_hook_share_asset_owner_boundary,
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
