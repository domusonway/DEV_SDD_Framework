#!/usr/bin/env python3
"""Layer 1: Challenger agent and challenge-gate routing docs."""
from pathlib import Path
import json
import subprocess
import sys


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
BRIEF = FRAMEWORK_ROOT / "docs/challenger_agent_BRIEF.md"
AGENTS = FRAMEWORK_ROOT / "AGENTS.md"
CHALLENGER = FRAMEWORK_ROOT / ".claude/agents/challenger.md"
CHALLENGE_GATE = FRAMEWORK_ROOT / ".claude/hooks/challenge-gate/HOOK.md"
CHALLENGE_GATE_RUN = FRAMEWORK_ROOT / ".claude/hooks/challenge-gate/run.py"
PLANNER = FRAMEWORK_ROOT / ".claude/agents/planner.md"
IMPLEMENTER = FRAMEWORK_ROOT / ".claude/agents/implementer.md"
REVIEWER = FRAMEWORK_ROOT / ".claude/agents/reviewer.md"
POST_GREEN = FRAMEWORK_ROOT / ".claude/hooks/post-green/HOOK.md"
SESSION_SNAPSHOT = FRAMEWORK_ROOT / ".claude/hooks/session-snapshot/HOOK.md"
CONTEXT_PROBE_SKILL = FRAMEWORK_ROOT / ".claude/skills/context-probe/SKILL.md"


def active_project_root() -> Path:
    project = ""
    project_path = ""
    for candidate in [FRAMEWORK_ROOT / "AGENTS.md", FRAMEWORK_ROOT / "CLAUDE.md"]:
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("PROJECT:") and not project:
                project = stripped.split(":", 1)[1].strip()
            if stripped.startswith("PROJECT_PATH:") and not project_path:
                project_path = stripped.split(":", 1)[1].strip()
        if project:
            break
    project_root = project_path or f"projects/{project}"
    return FRAMEWORK_ROOT / project_root


CHALLENGE_REPORTS = sorted((active_project_root() / "memory" / "challenges").glob("*.md"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_brief_exists_and_defines_acceptance():
    content = read(BRIEF)
    for keyword in ["Challenger", "质疑", "触发", "验收1", "验收2", "验收3"]:
        assert keyword in content, f"BRIEF 缺少 {keyword}"


def test_challenger_agent_exists_with_roles_and_decisions():
    content = read(CHALLENGER)
    for keyword in ["产品经理", "验收经理", "真实用户"]:
        assert keyword in content, f"Challenger 缺少角色视角：{keyword}"
    for decision in ["pass", "pass_with_risk", "rework", "ask_user"]:
        assert decision in content, f"Challenger 缺少决策：{decision}"
    assert "[CHALLENGER]" in content
    assert "memory/challenges" in content


def test_challenger_uses_ai_first_schema():
    content = read(CHALLENGER)
    for field in [
        "challenge_report:",
        "complexity_mode:",
        "user_scenario:",
        "problem_type:",
        "content_scope:",
        "original_request:",
        "draft_conclusion:",
        "claims:",
        "evidence:",
        "challenges:",
        "target_claim:",
        "evidence_refs:",
    ]:
        assert field in content, f"Challenger AI-first schema 缺少字段：{field}"
    assert "blocking_questions:" not in content, "不应继续使用与持久化结构不一致的旧输出字段"


def test_existing_challenge_reports_follow_ai_first_schema():
    assert CHALLENGE_REPORTS, "active project memory/challenges should contain challenge reports"
    for path in CHALLENGE_REPORTS:
        content = read(path)
        for field in ["challenge_report:", "claims:", "evidence:", "challenges:", "decision:"]:
            assert field in content, f"{path.name} 缺少 AI-first 字段：{field}"
        assert "## 质疑矩阵" not in content, f"{path.name} 仍使用人类表格结构"


def test_challenge_gate_defines_trigger_policy_and_noise_control():
    content = read(CHALLENGE_GATE)
    for trigger in ["H 模式", "M 模式", "Planner", "Reviewer", "post-green", "RED > 2", "跨 session"]:
        assert trigger in content, f"challenge-gate 缺少触发条件：{trigger}"
    assert "最多 7 个问题" in content
    assert "最多 3 个阻塞问题" in content
    assert "不得扩大用户需求" in content


def run_gate(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(CHALLENGE_GATE_RUN), *args, "--json"],
        capture_output=True,
        text=True,
        cwd=str(FRAMEWORK_ROOT),
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["data"]


def test_challenge_gate_run_exists_and_syntax_ok():
    assert CHALLENGE_GATE_RUN.exists(), "challenge-gate/run.py 不存在"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(CHALLENGE_GATE_RUN)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_challenge_gate_run_triggers_for_delivery_conclusion():
    data = run_gate(
        "--task", "长任务复杂任务完成后准备输出交付就绪最终结论",
        "--stage", "delivery",
        "--mode", "H",
        "--evidence", "pytest passed; doc-template validate ok",
    )
    assert data["triggered"] is True
    assert "complex_mode" in data["reasons"]
    assert "delivery_stage" in data["reasons"]
    assert ".claude/agents/challenger.md" in data["recommended_files"]


def test_challenge_gate_run_skips_low_risk_simple_task():
    data = run_gate(
        "--task", "解释 git status 是什么",
        "--stage", "analysis",
        "--mode", "L",
        "--evidence", "n/a",
    )
    assert data["triggered"] is False
    assert data["decision"] == "skip"


def test_challenge_gate_run_triggers_red_over_two_and_missing_evidence():
    data = run_gate(
        "--task", "RED > 2 stuck-detector 后准备继续当前修复方向",
        "--stage", "green",
        "--mode", "M",
        "--red-count", "3",
    )
    assert data["triggered"] is True
    assert "red_over_two" in data["reasons"]
    assert "missing_evidence" in data["risk_flags"]


def test_challenge_gate_record_path_uses_project_path_for_workspace_project():
    data = run_gate(
        "--task", "准备交付结论",
        "--stage", "delivery",
        "--mode", "M",
        "--project", "agentplatform",
        "--session-slug", "workspace-path-check",
        "--evidence", "pytest passed",
    )
    assert data["triggered"] is True
    assert data["record_path"] == "projects/agentplatform_workspace/agentplatform/memory/challenges/workspace-path-check.md"


def test_framework_entrypoints_reference_challenger():
    agent_content = read(AGENTS)
    assert ".claude/agents/challenger.md" in agent_content
    assert ".claude/hooks/challenge-gate/HOOK.md" in agent_content


def test_agent_flow_docs_reference_challenge_gate():
    for path in [PLANNER, IMPLEMENTER, REVIEWER, POST_GREEN]:
        content = read(path)
        assert "challenge-gate" in content or "Challenger" in content, f"{path} 未接入 challenge-gate"


def test_session_and_context_probe_record_challenger():
    assert "challenge" in read(SESSION_SNAPSHOT).lower()
    context_probe = read(CONTEXT_PROBE_SKILL)
    assert "质疑" in context_probe
    assert ".claude/agents/challenger.md" in context_probe


if __name__ == "__main__":
    tests = [
        test_brief_exists_and_defines_acceptance,
        test_challenger_agent_exists_with_roles_and_decisions,
        test_challenger_uses_ai_first_schema,
        test_existing_challenge_reports_follow_ai_first_schema,
        test_challenge_gate_defines_trigger_policy_and_noise_control,
        test_challenge_gate_run_exists_and_syntax_ok,
        test_challenge_gate_run_triggers_for_delivery_conclusion,
        test_challenge_gate_run_skips_low_risk_simple_task,
        test_challenge_gate_run_triggers_red_over_two_and_missing_evidence,
        test_challenge_gate_record_path_uses_project_path_for_workspace_project,
        test_framework_entrypoints_reference_challenger,
        test_agent_flow_docs_reference_challenge_gate,
        test_session_and_context_probe_record_challenger,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
        except AssertionError as exc:
            print(f"  ❌ {test.__name__}: {exc}")
            failed += 1
        except FileNotFoundError as exc:
            print(f"  ❌ {test.__name__}: {exc}")
            failed += 1
    sys.exit(failed)
