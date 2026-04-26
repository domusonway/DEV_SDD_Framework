#!/usr/bin/env python3
"""
Layer 1: Meta-Skill Loop 组件文档结构测试
覆盖所有新增的 agents/hooks/tools/commands
"""
import subprocess
import sys
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).parent.parent.parent

# ── 路径常量 ────────────────────────────────────────────────────────────────
META_SKILL_AGENT = FRAMEWORK_ROOT / ".claude/agents/meta-skill-agent.md"
AGENT_AUDITOR = FRAMEWORK_ROOT / ".claude/agents/agent-auditor.md"
HOOK_OBSERVER_MD = FRAMEWORK_ROOT / ".claude/hooks/hook-observer/HOOK.md"
HOOK_OBSERVER_PY = FRAMEWORK_ROOT / ".claude/hooks/hook-observer/observe.py"
PERM_AUDITOR_MD = FRAMEWORK_ROOT / ".claude/hooks/permission-auditor/HOOK.md"
PERM_AUDITOR_PY = FRAMEWORK_ROOT / ".claude/hooks/permission-auditor/audit.py"
TEST_SYNC_MD = FRAMEWORK_ROOT / ".claude/hooks/test-sync/HOOK.md"
TEST_SYNC_PY = FRAMEWORK_ROOT / ".claude/hooks/test-sync/sync.py"
CHECK_TOOLS_SH = FRAMEWORK_ROOT / ".claude/hooks/verify-rules/check_tools.sh"
SKILL_TRACKER = FRAMEWORK_ROOT / ".claude/tools/skill-tracker/tracker.py"
SKILL_REVIEW_CMD = FRAMEWORK_ROOT / ".claude/commands/skill-review.md"
CANDIDATES_DIR = FRAMEWORK_ROOT / "memory/candidates"
SCHEMA = FRAMEWORK_ROOT / "memory/candidates/SCHEMA.md"
CHANGELOG = FRAMEWORK_ROOT / "memory/skill-changelog.md"
DOMAINS_TDD = FRAMEWORK_ROOT / "memory/domains/tdd_patterns/INDEX.md"
DOMAINS_TYPE = FRAMEWORK_ROOT / "memory/domains/type_safety/INDEX.md"
DOMAINS_CONC = FRAMEWORK_ROOT / "memory/domains/concurrency/INDEX.md"


# ── meta-skill-agent.md ─────────────────────────────────────────────────────
def test_meta_skill_agent_exists():
    assert META_SKILL_AGENT.exists(), f"meta-skill-agent.md 不存在"


def test_meta_skill_agent_has_six_signals():
    content = META_SKILL_AGENT.read_text()
    for signal in ["信号A", "信号B", "信号C", "信号D", "信号E", "信号F"]:
        assert signal in content, f"meta-skill-agent 缺少 {signal}"


def test_meta_skill_agent_has_safety_boundary():
    content = META_SKILL_AGENT.read_text()
    assert "只写" in content or "不允许直接修改" in content, \
        "meta-skill-agent 必须声明只写 candidates/，不直接修改框架文件"


def test_meta_skill_agent_has_dedup():
    content = META_SKILL_AGENT.read_text()
    assert "去重" in content or "已有候选" in content, \
        "meta-skill-agent 必须有候选去重逻辑"


# ── agent-auditor.md ─────────────────────────────────────────────────────────
def test_agent_auditor_exists():
    assert AGENT_AUDITOR.exists(), f"agent-auditor.md 不存在"


def test_agent_auditor_has_three_dimensions():
    content = AGENT_AUDITOR.read_text()
    for dim in ["Reviewer", "PLAN.md", "session 中断"]:
        assert dim in content, f"agent-auditor 缺少维度：{dim}"


def test_agent_auditor_activates_after_reviewer():
    content = AGENT_AUDITOR.read_text()
    assert "Reviewer" in content and "激活" in content, \
        "agent-auditor 应在 Reviewer 完成后激活"


# ── hook-observer ────────────────────────────────────────────────────────────
def test_hook_observer_md_exists():
    assert HOOK_OBSERVER_MD.exists()


def test_hook_observer_py_exists():
    assert HOOK_OBSERVER_PY.exists()


def test_hook_observer_py_syntax():
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(HOOK_OBSERVER_PY)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"observe.py 语法错误：{result.stderr}"


def test_hook_observer_has_trigger_registry():
    content = HOOK_OBSERVER_PY.read_text()
    assert "HOOK_TRIGGER_REGISTRY" in content, "observe.py 缺少触发条件注册表"
    assert "network-guard" in content, "注册表应包含 network-guard"


def test_hook_observer_detects_asyncio():
    content = HOOK_OBSERVER_PY.read_text()
    assert "asyncio" in content, "hook-observer 应检测 asyncio 漏触发"


def test_hook_observer_md_has_table():
    content = HOOK_OBSERVER_MD.read_text()
    assert "network-guard" in content and "asyncio" in content, \
        "HOOK.md 应包含已知可能漏触发的技术表格"


# ── permission-auditor ──────────────────────────────────────────────────────
def test_permission_auditor_md_exists():
    assert PERM_AUDITOR_MD.exists()


def test_permission_auditor_py_exists():
    assert PERM_AUDITOR_PY.exists()


def test_permission_auditor_py_syntax():
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(PERM_AUDITOR_PY)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"audit.py 语法错误：{result.stderr}"


def test_permission_auditor_has_permanent_deny():
    content = PERM_AUDITOR_PY.read_text()
    assert "PERMANENT_DENY" in content, "audit.py 必须定义永久 deny 列表"
    assert "git commit" in content, "git commit 必须在永久 deny 中"


def test_permission_auditor_md_has_absolute_deny_list():
    content = PERM_AUDITOR_MD.read_text()
    assert "git commit" in content and "永远保持 deny" in content, \
        "HOOK.md 必须声明绝对不提议放宽的规则"


# ── test-sync ────────────────────────────────────────────────────────────────
def test_test_sync_md_exists():
    assert TEST_SYNC_MD.exists()


def test_test_sync_py_exists():
    assert TEST_SYNC_PY.exists()


def test_test_sync_py_syntax():
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(TEST_SYNC_PY)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"sync.py 语法错误：{result.stderr}"


def test_test_sync_has_skill_to_test_mapping():
    content = TEST_SYNC_PY.read_text()
    assert "SKILL_TO_TEST" in content, "sync.py 必须有 skill → test 文件映射"
    assert "tdd-cycle" in content, "映射应包含 tdd-cycle"


def test_test_sync_md_triggers_after_promote():
    content = TEST_SYNC_MD.read_text()
    assert "promote" in content, "HOOK.md 应说明在 promote 后触发"


# ── check_tools.sh ──────────────────────────────────────────────────────────
def test_check_tools_exists():
    assert CHECK_TOOLS_SH.exists()


def test_check_tools_has_tool_signal_output():
    content = CHECK_TOOLS_SH.read_text()
    assert "TOOL_SIGNAL:" in content, "check_tools.sh 必须输出 TOOL_SIGNAL: 格式的信号"


def test_check_tools_has_five_checks():
    content = CHECK_TOOLS_SH.read_text()
    for check in ["handoff_orphan", "stale_in_progress", "sparse_checkpoints",
                  "candidate_backlog", "missing_changelog"]:
        assert check in content, f"check_tools.sh 缺少检测：{check}"


# ── skill-tracker ────────────────────────────────────────────────────────────
def test_skill_tracker_exists():
    assert SKILL_TRACKER.exists()


def test_skill_tracker_syntax():
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(SKILL_TRACKER)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"tracker.py 语法错误：{result.stderr}"


def test_skill_tracker_has_all_subcommands():
    result = subprocess.run(
        [sys.executable, str(SKILL_TRACKER), "--help"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    for cmd in ["candidates", "validate", "approve", "reject", "promote", "status", "defer", "archive", "project-only", "rollback-info", "validate-schema", "review-summary"]:
        assert cmd in output, f"tracker.py 缺少子命令：{cmd}"


def test_skill_tracker_has_promote_targets():
    content = SKILL_TRACKER.read_text()
    assert "PROMOTE_TARGETS" in content, "tracker.py 必须定义 promote 策略映射"
    assert "permission_relax" in content, "映射应包含权限类候选"


def test_skill_tracker_has_changelog_write():
    content = SKILL_TRACKER.read_text()
    assert "write_changelog_entry" in content or "changelog" in content.lower(), \
        "tracker.py promote 后必须写入 skill-changelog.md"


def test_skill_tracker_promote_has_marked_rollback_boundary():
    content = SKILL_TRACKER.read_text()
    assert "DEV_SDD:PROMOTE:BEGIN" in content, "promote 必须写入可回滚开始标记"
    assert "DEV_SDD:PROMOTE:END" in content, "promote 必须写入可回滚结束标记"
    assert "rollback_marker_begin" in content and "rollback-info" in content, "必须暴露 rollback 元数据和查询命令"


def test_skill_tracker_has_review_summary_recommendations():
    content = SKILL_TRACKER.read_text()
    assert "review-summary" in content, "skill-tracker 应提供候选审核摘要命令"
    assert "defer_until_more_evidence" in content, "审核摘要应能建议等待更多证据"
    assert "approve_or_promote" in content, "审核摘要应能建议批准或提升"


def test_skill_tracker_validates_confidence_consistency():
    content = SKILL_TRACKER.read_text()
    assert "confidence_mismatch" in content, "schema 校验应检测 confidence 与 validated_projects 数量不一致"
    assert "expected_confidence" in content, "schema 校验应计算期望 confidence"


# ── skill-review command ─────────────────────────────────────────────────────
def test_skill_review_command_exists():
    assert SKILL_REVIEW_CMD.exists()


def test_skill_review_has_approve_reject_flow():
    content = SKILL_REVIEW_CMD.read_text()
    for keyword in ["approve", "reject", "promote"]:
        assert keyword in content, f"skill-review 命令缺少：{keyword}"


# ── candidates/ directory ────────────────────────────────────────────────────
def test_candidates_dir_exists():
    assert CANDIDATES_DIR.exists(), "memory/candidates/ 目录不存在"


def test_candidates_schema_exists():
    assert SCHEMA.exists(), "memory/candidates/SCHEMA.md 不存在"


def test_schema_has_all_candidate_types():
    content = SCHEMA.read_text()
    for ctype in ["skill_rule", "hook_trigger", "agent_constraint",
                  "permission_relax", "test_stub"]:
        assert ctype in content, f"SCHEMA.md 缺少类型：{ctype}"


def test_schema_has_extended_review_lifecycle_and_rollback_fields():
    content = SCHEMA.read_text()
    for phrase in ["deferred", "archived", "project_only", "rollback_marker_begin", "review_history", "DEV_SDD:PROMOTE:BEGIN"]:
        assert phrase in content, f"SCHEMA.md 缺少候选生命周期/回滚字段：{phrase}"


# ── skill-changelog.md ───────────────────────────────────────────────────────
def test_skill_changelog_exists():
    assert CHANGELOG.exists(), "memory/skill-changelog.md 不存在"


def test_skill_changelog_has_format_template():
    content = CHANGELOG.read_text()
    assert "来源候选" in content or "candidate" in content.lower(), \
        "skill-changelog.md 应有格式模板"


# ── new domains ──────────────────────────────────────────────────────────────
def test_domain_tdd_patterns_exists():
    assert DOMAINS_TDD.exists()


def test_domain_type_safety_exists():
    assert DOMAINS_TYPE.exists()


def test_domain_concurrency_exists():
    assert DOMAINS_CONC.exists()


def test_domains_have_candidate_zone():
    for path in [DOMAINS_TDD, DOMAINS_TYPE, DOMAINS_CONC]:
        content = path.read_text()
        assert "候选规则区" in content, f"{path.name} 缺少候选规则区"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__} [ERROR]: {e}")
            failed += 1
    print(f"\n{'─'*50}")
    print(f"  {len(tests) - failed}/{len(tests)} 通过")
    sys.exit(failed)
