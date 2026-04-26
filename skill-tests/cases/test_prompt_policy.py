#!/usr/bin/env python3
from __future__ import annotations

"""Layer 1: prompt-policy skill structure tests."""

from pathlib import Path
import json
import subprocess
import sys


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_PATH = FRAMEWORK_ROOT / ".claude/skills/prompt-policy/SKILL.md"
AGENTS_PATH = FRAMEWORK_ROOT / "AGENTS.md"
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/prompt-policy/run.py"


def test_skill_exists():
    assert SKILL_PATH.exists(), f"prompt-policy SKILL 不存在: {SKILL_PATH}"


def test_has_required_task_classes():
    content = SKILL_PATH.read_text(encoding="utf-8")
    for task_class in [
        "review_evaluate_analyze",
        "doc_creation",
        "planning_parallel",
        "memory_review",
        "implementation_fix",
    ]:
        assert task_class in content, f"缺少任务大类: {task_class}"


def test_review_policy_requires_comprehensive_accurate_clear_metrics():
    content = SKILL_PATH.read_text(encoding="utf-8")
    for phrase in ["全面", "准确", "清晰", "指标", "残余风险"]:
        assert phrase in content, f"审查/评估/分析约束缺少: {phrase}"


def test_doc_policy_requires_location_truth_source_and_language_policy():
    content = SKILL_PATH.read_text(encoding="utf-8")
    for phrase in ["doc-template", "root docs/", "projects/<PROJECT>/docs/", "docs/sub_docs/", "真相源", "validate", "默认尽可能使用中文", "专业术语"]:
        assert phrase in content, f"文档创建约束缺少: {phrase}"


def test_parallel_policy_mentions_dependency_owner_conflict_merge_gate():
    content = SKILL_PATH.read_text(encoding="utf-8")
    for phrase in ["deps/blocked_by", "owner", "shared artifacts", "writes/reads", "merge gate"]:
        assert phrase in content, f"并行规划约束缺少: {phrase}"


def test_memory_policy_mentions_evidence_scope_lifecycle():
    content = SKILL_PATH.read_text(encoding="utf-8")
    for phrase in ["evidence", "scope", "confidence", "validated_projects", "rollback/deprecate"]:
        assert phrase in content, f"记忆审核约束缺少: {phrase}"


def test_output_block_is_explicit_and_bounded():
    content = SKILL_PATH.read_text(encoding="utf-8")
    assert "[PROMPT-POLICY]" in content, "必须定义显式输出块"
    assert "最多注入 3 组" in content or "超过 3 类" in content, "必须限制注入数量避免上下文污染"
    assert "不得隐藏注入内容" in content, "必须禁止隐藏注入"


def test_agents_startup_loads_prompt_policy():
    content = AGENTS_PATH.read_text(encoding="utf-8")
    assert ".claude/skills/prompt-policy/SKILL.md" in content, "启动协议应加载 prompt-policy"
    assert "prompt-policy" in content, "AGENTS.md 应声明 prompt-policy"


def test_prompt_policy_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"prompt-policy helper 不存在: {TOOL_PATH}"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, f"prompt-policy helper 语法错误: {result.stderr}"


def test_prompt_policy_tool_classifies_multiple_high_priority_categories():
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "请审查 plan.json 多模块并行规划和经验沉淀人工审核", "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    matched = payload["data"]["matched"]
    assert "planning_parallel" in matched
    assert "memory_review" in matched
    assert "review_evaluate_analyze" in matched
    assert len(matched) <= 3, "注入策略不得超过 3 类"


def test_prompt_policy_tool_doc_creation_injects_doc_template():
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "请创建一个模块验证报告", "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "doc_creation" in payload["data"]["matched"]
    injected = "\n".join(payload["data"]["injected"])
    assert "doc-template" in injected
    assert "[DOC-TEMPLATE]" in injected
    assert "validate" in injected
    assert "默认尽可能使用中文" in injected


if __name__ == "__main__":
    tests = [
        test_skill_exists,
        test_has_required_task_classes,
        test_review_policy_requires_comprehensive_accurate_clear_metrics,
        test_doc_policy_requires_location_truth_source_and_language_policy,
        test_parallel_policy_mentions_dependency_owner_conflict_merge_gate,
        test_memory_policy_mentions_evidence_scope_lifecycle,
        test_output_block_is_explicit_and_bounded,
        test_agents_startup_loads_prompt_policy,
        test_prompt_policy_tool_exists_and_syntax_ok,
        test_prompt_policy_tool_classifies_multiple_high_priority_categories,
        test_prompt_policy_tool_doc_creation_injects_doc_template,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
        except AssertionError as exc:
            print(f"  ❌ {test.__name__}: {exc}")
            failed += 1
    sys.exit(failed)
