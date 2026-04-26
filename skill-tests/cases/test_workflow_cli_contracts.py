#!/usr/bin/env python3
from __future__ import annotations

"""
skill-tests/cases/test_workflow_cli_contracts.py
Layer 1: Workflow helper CLI shared contract tests

用途:
  验证 INIT / REDEFINE / UPDATE_TODO / START_WORK / FIX 的共享 CLI 契约：
  - --json 输出统一为 {status,message,data}
  - status 仅允许 ok|warning|error
  - repo-relative 项目输入在 repo root 与嵌套 cwd 下解析一致
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECTS_DIR = FRAMEWORK_ROOT / "projects"

INIT_TOOL = FRAMEWORK_ROOT / ".claude/tools/init/run.py"
REDEFINE_TOOL = FRAMEWORK_ROOT / ".claude/tools/redefine/run.py"
UPDATE_TODO_TOOL = FRAMEWORK_ROOT / ".claude/tools/update-todo/run.py"
START_WORK_TOOL = FRAMEWORK_ROOT / ".claude/tools/start-work/run.py"
FIX_TOOL = FRAMEWORK_ROOT / ".claude/tools/fix/run.py"

INIT_FIXTURES = FRAMEWORK_ROOT / "skill-tests/fixtures/init"
REDEFINE_FIXTURES = FRAMEWORK_ROOT / "skill-tests/fixtures/redefine"
UPDATE_TODO_FIXTURES = FRAMEWORK_ROOT / "skill-tests/fixtures/update_todo"
FIX_FIXTURES = FRAMEWORK_ROOT / "skill-tests/fixtures/fix"


def run_tool(tool_path: Path, *args: str, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, str(tool_path), *[str(arg) for arg in args]],
        capture_output=True,
        text=True,
        cwd=str(cwd or FRAMEWORK_ROOT),
    )


def parse_json_output(result, name: str):
    assert result.stdout.strip(), f"{name} 无输出"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        assert False, f"{name} 输出不是合法 JSON: {exc}\n{result.stdout[:200]}"

    assert set(payload.keys()) == {"status", "message", "data"}, (
        f"{name} 顶层 envelope 应仅包含 status/message/data: {payload.keys()}"
    )
    assert payload["status"] in ("ok", "warning", "error"), f"{name} status 非法: {payload['status']}"
    assert isinstance(payload["message"], str), f"{name} message 必须为字符串"
    assert isinstance(payload["data"], dict), f"{name} data 必须为对象"
    return payload


def clone_project_fixture(fixtures_root: Path, fixture_name: str, prefix: str) -> Path:
    source = fixtures_root / fixture_name
    assert source.exists(), f"fixture 不存在: {source}"
    temp_root = Path(tempfile.mkdtemp(prefix=f"{prefix}_", dir=str(PROJECTS_DIR)))
    project_root = temp_root / fixture_name
    shutil.copytree(source, project_root)
    return project_root


def make_start_work_project() -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="workflow_start_work_", dir=str(PROJECTS_DIR)))
    project_root = temp_root / "workflow-start-work-project"
    (project_root / "docs").mkdir(parents=True, exist_ok=True)
    (project_root / "memory" / "sessions").mkdir(parents=True, exist_ok=True)
    (project_root / "CLAUDE.md").write_text("# workflow-start-work-project\n工作模式: M 标准\n", encoding="utf-8")
    (project_root / "memory" / "INDEX.md").write_text("# memory\n", encoding="utf-8")
    (project_root / "docs" / "plan.json").write_text(
        json.dumps({
            "project": project_root.name,
            "batches": [
                {
                    "name": "Batch 1",
                    "modules": [
                        {"id": "T-001", "name": "module_alpha", "state": "pending"},
                        {"id": "T-002", "name": "module_beta", "state": "in_progress"},
                    ],
                }
            ],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return project_root


def build_fix_issue(project_root: Path, project_ref: str) -> Path:
    payload = json.loads((FIX_FIXTURES / "repro-issue.json").read_text(encoding="utf-8"))
    payload["project"] = project_ref
    issue_path = project_root.parent / "workflow-fix-issue.json"
    issue_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return issue_path


def cleanup_project_root(project_root: Path) -> None:
    shutil.rmtree(project_root.parent, ignore_errors=True)


def repo_relative(path: Path) -> str:
    return path.relative_to(FRAMEWORK_ROOT).as_posix()


def test_json_envelope_consistent_across_workflow_helpers():
    init_project = clone_project_fixture(INIT_FIXTURES, "empty-project", "workflow_init")
    redefine_project = clone_project_fixture(REDEFINE_FIXTURES, "plan-change-project", "workflow_redefine")
    update_project = clone_project_fixture(UPDATE_TODO_FIXTURES, "partial-merge-project", "workflow_update")
    start_work_project = make_start_work_project()
    fix_project = clone_project_fixture(FIX_FIXTURES, "repro-project", "workflow_fix")
    fix_issue = build_fix_issue(fix_project, fix_project.name)

    try:
        cases = [
            ("INIT", INIT_TOOL, [str(init_project), "--json", "--dry-run"]),
            ("REDEFINE", REDEFINE_TOOL, [str(redefine_project), "--json", "--dry-run"]),
            ("UPDATE_TODO", UPDATE_TODO_TOOL, [str(update_project), "--ids", "T-002,T-004", "--json", "--dry-run"]),
            ("START_WORK", START_WORK_TOOL, [start_work_project.name, "--json"]),
            ("FIX", FIX_TOOL, [str(fix_issue), "--json", "--dry-run"]),
        ]

        for label, tool_path, args in cases:
            result = run_tool(tool_path, *args)
            assert result.returncode == 0, f"{label} --json 应成功: {result.stderr}"
            payload = parse_json_output(result, label)
            assert payload["data"], f"{label} data 不应为空对象"
    finally:
        cleanup_project_root(init_project)
        cleanup_project_root(redefine_project)
        cleanup_project_root(update_project)
        cleanup_project_root(start_work_project)
        cleanup_project_root(fix_project)


def test_repo_relative_project_resolution_is_stable_across_working_directories():
    init_project = clone_project_fixture(INIT_FIXTURES, "empty-project", "workflow_init_resolution")
    redefine_project = clone_project_fixture(REDEFINE_FIXTURES, "plan-change-project", "workflow_redefine_resolution")
    update_project = clone_project_fixture(UPDATE_TODO_FIXTURES, "partial-merge-project", "workflow_update_resolution")
    start_work_project = make_start_work_project()
    fix_project = clone_project_fixture(FIX_FIXTURES, "repro-project", "workflow_fix_resolution")

    try:
        init_arg = repo_relative(init_project)
        redefine_arg = repo_relative(redefine_project)
        update_arg = repo_relative(update_project)
        start_work_arg = repo_relative(start_work_project)
        fix_project_arg = repo_relative(fix_project)
        fix_issue = build_fix_issue(fix_project, fix_project_arg)

        cases = [
            ("INIT", INIT_TOOL, [init_arg, "--json", "--dry-run"], init_project, "project_root"),
            ("REDEFINE", REDEFINE_TOOL, [redefine_arg, "--json", "--dry-run"], redefine_project, "project_root"),
            ("UPDATE_TODO", UPDATE_TODO_TOOL, [update_arg, "--ids", "T-002,T-004", "--json", "--dry-run"], update_project, "project_root"),
            ("START_WORK", START_WORK_TOOL, [start_work_arg, "--json"], start_work_project, "project_path"),
            ("FIX", FIX_TOOL, [str(fix_issue), "--json", "--dry-run"], fix_project, "project_root"),
        ]

        for label, tool_path, args, project_root, path_key in cases:
            from_root = run_tool(tool_path, *args, cwd=FRAMEWORK_ROOT)
            from_nested = run_tool(tool_path, *args, cwd=project_root / "docs")

            assert from_root.returncode == 0, f"{label} repo root 运行失败: {from_root.stderr}"
            assert from_nested.returncode == 0, f"{label} nested cwd 运行失败: {from_nested.stderr}"

            root_payload = parse_json_output(from_root, f"{label} repo root")
            nested_payload = parse_json_output(from_nested, f"{label} nested cwd")

            expected_rel = repo_relative(project_root)
            assert root_payload["data"][path_key] == expected_rel, (
                f"{label} repo root 应解析到 {expected_rel}: {root_payload['data'][path_key]}"
            )
            assert nested_payload["data"][path_key] == expected_rel, (
                f"{label} nested cwd 应解析到 {expected_rel}: {nested_payload['data'][path_key]}"
            )
            assert root_payload["data"][path_key] == nested_payload["data"][path_key], (
                f"{label} 不同 cwd 下解析结果应一致"
            )
    finally:
        cleanup_project_root(init_project)
        cleanup_project_root(redefine_project)
        cleanup_project_root(update_project)
        cleanup_project_root(start_work_project)
        cleanup_project_root(fix_project)


def test_init_outputs_plan_and_sub_docs_are_consumable_by_start_work_and_update_todo():
    init_project = clone_project_fixture(INIT_FIXTURES, "empty-project", "workflow_init_integration")
    try:
        project_arg = repo_relative(init_project)

        init_result = run_tool(INIT_TOOL, project_arg, "--json")
        assert init_result.returncode == 0, f"INIT 实际执行失败: {init_result.stderr}"
        init_payload = parse_json_output(init_result, "INIT integration")
        assert init_payload["status"] == "ok"

        assert not (init_project / "docs" / "TODO.md").exists(), "INIT 不应再生成 docs/TODO.md"
        assert (init_project / "docs" / "sub_docs").exists(), "INIT 应生成 docs/sub_docs"

        start_work = run_tool(START_WORK_TOOL, project_arg, "--json")
        assert start_work.returncode == 0, f"START_WORK 读取 INIT 产物失败: {start_work.stderr}"
        start_payload = parse_json_output(start_work, "START_WORK integration")
        reconciliation = start_payload["data"].get("reconciliation") or {}
        assert reconciliation.get("status") == "not_applicable", f"TODO 废弃后应跳过 TODO 对账: {reconciliation}"

        plan = json.loads((init_project / "docs" / "plan.json").read_text(encoding="utf-8"))
        first_id = plan["batches"][0]["modules"][0]["id"]
        update_result = run_tool(UPDATE_TODO_TOOL, project_arg, "--ids", first_id, "--json", "--dry-run")
        assert update_result.returncode == 0, f"UPDATE_TODO 读取 INIT 产物失败: {update_result.stderr}"
        update_payload = parse_json_output(update_result, "UPDATE_TODO integration")
        assert update_payload["status"] == "ok"
        assert update_payload["data"].get("deprecated") is True
        writes = {item["path"]: item["action"] for item in update_payload["data"].get("writes", [])}
        assert "docs/plan.json" in writes
    finally:
        cleanup_project_root(init_project)


if __name__ == "__main__":
    tests = [
        test_json_envelope_consistent_across_workflow_helpers,
        test_repo_relative_project_resolution_is_stable_across_working_directories,
        test_init_outputs_plan_and_sub_docs_are_consumable_by_start_work_and_update_todo,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
        except AssertionError as exc:
            print(f"  ❌ {test.__name__}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"  ❌ {test.__name__} [ERROR]: {exc}")
            failed += 1
    print(f"\n{'─'*50}")
    print(f"  {len(tests) - failed}/{len(tests)} 通过")
    sys.exit(failed)
