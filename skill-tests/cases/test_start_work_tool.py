#!/usr/bin/env python3
"""
skill-tests/cases/test_start_work_tool.py
Layer 1: /DEV_SDD:start-work 辅助 CLI 合规测试

用途:
  验证 .claude/tools/start-work/run.py 的接口与降级行为：
  - 语法与 --help 章节
  - --json 输出 schema: {status,message,data}
  - 无参数读取激活项目
  - 显式项目覆盖 + 缺失项目降级
  - 计划优先级: plan.json > PLAN.md > IMPLEMENTATION_PLAN.md
  - HANDOFF/session 状态探测
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/start-work/run.py"


def run_tool(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(TOOL_PATH)] + list(args),
        capture_output=True,
        text=True,
        cwd=str(cwd or FRAMEWORK_ROOT),
    )


def parse_json_output(result, name):
    assert result.stdout.strip(), f"{name} 无输出"
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        assert False, f"{name} 输出不是合法 JSON: {e}\n{result.stdout[:200]}"
    assert "status" in data, f"{name} 缺少 status"
    assert "message" in data, f"{name} 缺少 message"
    assert "data" in data, f"{name} 缺少 data"
    assert data["status"] in ("ok", "warning", "error"), f"{name} status 非法: {data['status']}"
    return data


def _mk_project(name: str):
    projects_dir = FRAMEWORK_ROOT / "projects"
    p = Path(tempfile.mkdtemp(prefix=f"{name}_", dir=str(projects_dir)))
    (p / "docs").mkdir(parents=True, exist_ok=True)
    (p / "memory").mkdir(parents=True, exist_ok=True)
    (p / "memory" / "sessions").mkdir(parents=True, exist_ok=True)
    (p / "CLAUDE.md").write_text("# test\n工作模式: M 标准\n", encoding="utf-8")
    (p / "memory" / "INDEX.md").write_text("# mem\n", encoding="utf-8")
    return p


def _write_plan_json(project_root: Path, modules: list[dict[str, str]]):
    (project_root / "docs" / "plan.json").write_text(
        json.dumps({
            "project": project_root.name,
            "batches": [
                {
                    "name": "Batch 1",
                    "modules": modules,
                }
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_managed_todo(project_root: Path, lines: list[str]):
    todo = [
        f"# {project_root.name} · 任务跟踪",
        "",
        "> ⚠️ 执行状态以 `docs/plan.json` 为准；此文件仅记录项目级备注、审计和人工跟进。",
        "",
        "<!-- DEV_SDD:MANAGED:BEGIN -->",
        *lines,
        "<!-- DEV_SDD:MANAGED:END -->",
        "",
        "<!-- DEV_SDD:USER_NOTES:BEGIN -->",
        "## 用户备注",
        "- fixture notes",
        "<!-- DEV_SDD:USER_NOTES:END -->",
        "",
    ]
    (project_root / "docs" / "TODO.md").write_text("\n".join(todo), encoding="utf-8")


def _mk_external_project(name: str):
    p = Path(tempfile.mkdtemp(prefix=f"{name}_"))
    (p / "docs").mkdir(parents=True, exist_ok=True)
    (p / "memory" / "sessions").mkdir(parents=True, exist_ok=True)
    (p / "CLAUDE.md").write_text("# external test\n工作模式: M 标准\n", encoding="utf-8")
    (p / "memory" / "INDEX.md").write_text("# external mem\n", encoding="utf-8")
    return p


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"run.py 不存在: {TOOL_PATH}"
    res = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert res.returncode == 0, f"run.py 语法错误: {res.stderr}"


def test_help_contains_usage_and_example():
    res = run_tool("--help")
    out = res.stdout + res.stderr
    assert "用途" in out, "--help 缺少「用途」"
    assert "示例" in out or "example" in out.lower(), "--help 缺少「示例」"


def test_json_output_schema_on_active_project():
    res = run_tool("--json")
    assert res.returncode == 0, f"--json 运行失败: {res.stderr}"
    data = parse_json_output(res, "start-work --json")
    assert isinstance(data["data"], dict), "data 必须是对象"
    assert "project" in data["data"], "data 缺少 project"
    assert "next_action" in data["data"], "data 缺少 next_action"


def test_no_arg_uses_active_project_from_framework_context():
    res = run_tool("--json")
    data = parse_json_output(res, "start-work active project")
    assert data["data"].get("project") == "structured-light-stereo", "无参数时应使用当前激活项目"


def test_explicit_project_override_and_missing_data_degrade_gracefully():
    name = "missing_start_work_project_xyz"
    res = run_tool(name, "--json")
    assert res.returncode == 0, "缺失项目应降级 warning，不应崩溃"
    data = parse_json_output(res, "start-work missing project")
    assert data["status"] == "warning", "缺失项目时应为 warning"
    assert data["data"].get("project") == name, "显式项目名应被保留"
    assert data["data"].get("next_action"), "缺失项目时也应给出 next_action"


def test_plan_priority_prefers_plan_json_then_markdown_fallbacks():
    p = _mk_project("start_work_plan_priority")
    try:
        project = p.name
        (p / "docs" / "plan.json").write_text(
            json.dumps({
                "project": project,
                "batches": [
                    {"name": "Batch 1", "modules": [{"name": "m1", "state": "completed"}]},
                    {"name": "Batch 2", "modules": [{"name": "m2", "state": "pending"}]},
                ],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        (p / "docs" / "PLAN.md").write_text("- [ ] SHOULD_NOT_WIN\n", encoding="utf-8")
        (p / "docs" / "IMPLEMENTATION_PLAN.md").write_text("- [ ] SHOULD_NOT_WIN_EITHER\n", encoding="utf-8")
        res1 = run_tool(project, "--json")
        d1 = parse_json_output(res1, "start-work plan priority #1")
        assert d1["data"]["plan"]["source"] == "plan.json", "应优先使用 plan.json"
        assert "m2" in d1["data"]["plan"]["next_action"], "next_action 应来自 plan.json"

        (p / "docs" / "plan.json").unlink()
        (p / "docs" / "PLAN.md").write_text("- [ ] PLAN_FALLBACK_TASK\n", encoding="utf-8")
        res2 = run_tool(project, "--json")
        d2 = parse_json_output(res2, "start-work plan priority #2")
        assert d2["data"]["plan"]["source"] == "PLAN.md", "无 plan.json 时应使用 PLAN.md"
        assert "PLAN_FALLBACK_TASK" in d2["data"]["plan"]["next_action"]

        (p / "docs" / "PLAN.md").unlink()
        (p / "docs" / "IMPLEMENTATION_PLAN.md").write_text("- [ ] IMPL_PLAN_TASK\n", encoding="utf-8")
        res3 = run_tool(project, "--json")
        d3 = parse_json_output(res3, "start-work plan priority #3")
        assert d3["data"]["plan"]["source"] == "IMPLEMENTATION_PLAN.md", "应回退到 IMPLEMENTATION_PLAN.md"
        assert "IMPL_PLAN_TASK" in d3["data"]["plan"]["next_action"]
    finally:
        shutil.rmtree(p, ignore_errors=True)


def test_session_state_prefers_handoff_then_in_progress_session():
    p = _mk_project("start_work_session_state")
    try:
        project = p.name
        (p / "docs" / "PLAN.md").write_text("- [ ] task-a\n", encoding="utf-8")

        (p / "memory" / "sessions" / "2099-01-01_00-01.md").write_text(
            "---\nstatus: in-progress\ntask: test-task\n---\n\n下次继续: 继续 test-task\n",
            encoding="utf-8",
        )
        res1 = run_tool(project, "--json")
        d1 = parse_json_output(res1, "start-work session #1")
        assert d1["data"]["session"]["state"] == "RESUME", "in-progress session 应触发 RESUME"

        (p / "HANDOFF.json").write_text(
            json.dumps({"next_action": "from handoff", "timestamp": "2026-01-01T00:00:00"}, ensure_ascii=False),
            encoding="utf-8",
        )
        res2 = run_tool(project, "--json")
        d2 = parse_json_output(res2, "start-work session #2")
        assert d2["data"]["session"]["handoff_exists"] is True
        assert d2["data"]["session"]["state"] == "RESUME"
        assert d2["data"]["next_action"] == "from handoff", "handoff 应覆盖下一步动作"
    finally:
        shutil.rmtree(p, ignore_errors=True)


def test_reconciliation_aligned_todo_reports_no_warnings_and_plan_authoritative_next_action():
    p = _mk_project("start_work_reconcile_aligned")
    try:
        project = p.name
        _write_plan_json(p, [
            {"id": "T-001", "name": "module_alpha", "state": "pending"},
            {"id": "T-002", "name": "module_beta", "state": "in_progress"},
        ])
        _write_managed_todo(p, [
            "- [ ] module_alpha <!-- DEV_SDD:TASK:id=T-001;name=module_alpha;state=pending -->",
            "- [>] module_beta <!-- DEV_SDD:TASK:id=T-002;name=module_beta;state=in_progress -->",
        ])

        res = run_tool(project, "--json")
        data = parse_json_output(res, "start-work reconciliation aligned")

        assert data["data"].get("next_action_source") == "plan.json", "next_action 来源应标注为 plan.json"
        assert "module_alpha" in data["data"].get("next_action", ""), "next_action 必须来自 plan 顺序"

        rec = data["data"].get("reconciliation") or {}
        assert rec.get("status") == "aligned"
        assert rec.get("matched_ids") == ["T-001", "T-002"]
        assert rec.get("orphan_ids") == []
        assert rec.get("conflict_ids") == []
        assert rec.get("warnings") == []
    finally:
        shutil.rmtree(p, ignore_errors=True)


def test_reconciliation_mismatch_reports_deterministic_warnings_without_overriding_plan_next_action():
    p = _mk_project("start_work_reconcile_mismatch")
    try:
        project = p.name
        _write_plan_json(p, [
            {"id": "T-001", "name": "module_alpha", "state": "pending"},
            {"id": "T-002", "name": "module_beta", "state": "completed"},
            {"id": "T-003", "name": "module_gamma", "state": "pending"},
        ])
        _write_managed_todo(p, [
            "- [x] module_alpha_renamed <!-- DEV_SDD:TASK:id=T-001;name=module_alpha_renamed;state=completed -->",
            "- [x] module_beta <!-- DEV_SDD:TASK:id=T-002;name=module_beta;state=completed -->",
            "- [x] module_beta_duplicate <!-- DEV_SDD:TASK:id=T-002;name=module_beta_duplicate;state=completed -->",
            "- [ ] orphan_task <!-- DEV_SDD:TASK:id=T-404;name=orphan_task;state=pending -->",
        ])

        res = run_tool(project, "--json")
        data = parse_json_output(res, "start-work reconciliation mismatch")
        rec = data["data"].get("reconciliation") or {}

        assert data["data"].get("next_action_source") == "plan.json"
        assert "module_alpha" in data["data"].get("next_action", ""), "TODO 冲突时也应以 plan next_action 为准"

        warnings = rec.get("warnings") or []
        reasons = [item.get("reason") for item in warnings]
        assert "duplicate_todo_id" in reasons
        assert "orphan_todo_id" in reasons
        assert "missing_todo_id" in reasons
        assert "state_mismatch" in reasons
        assert "name_mismatch" in reasons

        assert "T-404" in (rec.get("orphan_ids") or [])
        assert "T-001" in (rec.get("conflict_ids") or [])
        assert rec.get("status") == "mismatch"
    finally:
        shutil.rmtree(p, ignore_errors=True)


def test_reconciliation_without_todo_file_reports_warning_but_uses_plan_next_action():
    p = _mk_project("start_work_reconcile_no_todo")
    try:
        project = p.name
        _write_plan_json(p, [
            {"id": "T-001", "name": "module_alpha", "state": "pending"},
        ])

        res = run_tool(project, "--json")
        data = parse_json_output(res, "start-work reconciliation no todo")
        rec = data["data"].get("reconciliation") or {}

        assert data["data"].get("next_action_source") == "plan.json"
        assert "module_alpha" in data["data"].get("next_action", "")
        assert rec.get("status") == "todo_missing"
        warnings = rec.get("warnings") or []
        assert any(item.get("reason") == "todo_missing" for item in warnings)
    finally:
        shutil.rmtree(p, ignore_errors=True)


def test_absolute_external_project_path_returns_json_without_crashing():
    p = _mk_external_project("start_work_external_absolute")
    try:
        _write_plan_json(p, [
            {"id": "T-001", "name": "module_alpha", "state": "pending"},
            {"id": "T-002", "name": "module_beta", "state": "in_progress"},
        ])
        _write_managed_todo(p, [
            "- [ ] module_alpha <!-- DEV_SDD:TASK:id=T-001;name=module_alpha;state=pending -->",
            "- [>] module_beta <!-- DEV_SDD:TASK:id=T-002;name=module_beta;state=in_progress -->",
        ])
        (p / "memory" / "sessions" / "2099-01-01_00-01.md").write_text(
            "---\nstatus: in-progress\ntask: external-task\n---\n\n下次继续: 继续 external-task\n",
            encoding="utf-8",
        )

        res = run_tool(str(p), "--json")
        assert res.returncode == 0, f"absolute external path 不应崩溃: {res.stderr}"
        data = parse_json_output(res, "start-work external absolute path")

        assert data["data"].get("project") == p.name, "absolute path 应保留外部项目目录名"
        assert data["data"].get("project_path") == str(p.resolve()), "外部项目 project_path 应允许返回绝对路径"
        assert data["data"].get("plan", {}).get("source") == "plan.json"
        assert data["data"].get("session", {}).get("state") == "RESUME"
        assert data["data"].get("context_files", {}).get("project"), "外部项目也应返回项目上下文文件"
    finally:
        shutil.rmtree(p, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_tool_exists_and_syntax_ok,
        test_help_contains_usage_and_example,
        test_json_output_schema_on_active_project,
        test_no_arg_uses_active_project_from_framework_context,
        test_explicit_project_override_and_missing_data_degrade_gracefully,
        test_plan_priority_prefers_plan_json_then_markdown_fallbacks,
        test_session_state_prefers_handoff_then_in_progress_session,
        test_reconciliation_aligned_todo_reports_no_warnings_and_plan_authoritative_next_action,
        test_reconciliation_mismatch_reports_deterministic_warnings_without_overriding_plan_next_action,
        test_reconciliation_without_todo_file_reports_warning_but_uses_plan_next_action,
        test_absolute_external_project_path_returns_json_without_crashing,
    ]
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
