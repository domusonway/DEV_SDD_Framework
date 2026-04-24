#!/usr/bin/env python3
"""
skill-tests/cases/test_update_todo_tool.py
Layer 1: DEV_SDD:UPDATE_TODO helper CLI 合规测试

用途:
  验证 .claude/tools/update-todo/run.py 的新约束：
  - docs/TODO.md 已废弃，本工具不再写入 TODO
  - 仅维护 docs/plan.json 的 stable IDs
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/update-todo/run.py"
FIXTURES_ROOT = FRAMEWORK_ROOT / "skill-tests/fixtures/update_todo"


def run_tool(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(TOOL_PATH)] + [str(arg) for arg in args],
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


def clone_fixture(name: str) -> Path:
    source = FIXTURES_ROOT / name
    assert source.exists(), f"fixture 不存在: {source}"
    temp_dir = Path(tempfile.mkdtemp(prefix=f"{name}_"))
    target = temp_dir / name
    shutil.copytree(source, target)
    return target


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"run.py 不存在: {TOOL_PATH}"
    res = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert res.returncode == 0, f"run.py 语法错误: {res.stderr}"


def test_help_contains_usage_and_example():
    res = run_tool("--help")
    out = res.stdout + res.stderr
    assert "用途" in out, "--help 缺少「用途」"
    assert "示例" in out or "example" in out.lower(), "--help 缺少「示例」"


def test_dry_run_reports_todo_deprecated_and_only_plan_write():
    project_root = clone_fixture("partial-merge-project")
    try:
        preview_res = run_tool(project_root, "--ids", "T-002,T-004", "--json", "--dry-run")
        assert preview_res.returncode == 0, f"dry-run 失败: {preview_res.stderr}"
        preview = parse_json_output(preview_res, "update-todo dry-run")
        assert preview["status"] == "ok"
        assert preview["data"].get("deprecated") is True
        assert preview["data"].get("plan_source") == "docs/plan.json"
        assert preview["data"].get("selected_ids") == ["T-002", "T-004"]
        writes = {item["path"]: item["action"] for item in preview["data"].get("writes", [])}
        assert set(writes.keys()) == {"docs/plan.json"}, f"不应包含 docs/TODO.md 写入: {writes}"
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


def test_actual_run_injects_missing_stable_ids_but_does_not_touch_todo_file():
    project_root = clone_fixture("partial-merge-project")
    try:
        todo_path = project_root / "docs/TODO.md"
        todo_before = todo_path.read_text(encoding="utf-8")

        actual_res = run_tool(project_root, "--ids", "T-002,T-004", "--json")
        assert actual_res.returncode == 0, f"actual run 失败: {actual_res.stderr}"
        result = parse_json_output(actual_res, "update-todo actual")
        assert result["status"] == "ok"

        plan = json.loads((project_root / "docs/plan.json").read_text(encoding="utf-8"))
        module_ids = {
            module["name"]: module.get("id")
            for batch in plan.get("batches", [])
            for module in batch.get("modules", [])
        }
        assert module_ids.get("module_delta") == "T-004", "缺失 ID 的任务应被注入并持久化到 plan.json"

        todo_after = todo_path.read_text(encoding="utf-8")
        assert todo_after == todo_before, "UPDATE_TODO 不应改写 docs/TODO.md"
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


def test_invalid_selected_id_returns_error():
    project_root = clone_fixture("partial-merge-project")
    try:
        res = run_tool(project_root, "--ids", "T-999", "--json")
        assert res.returncode == 1, "请求不存在 ID 时应返回 error 退出码"
        payload = parse_json_output(res, "update-todo invalid id")
        assert payload["status"] == "error"
        assert payload["data"].get("missing_ids") == ["T-999"]
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_tool_exists_and_syntax_ok,
        test_help_contains_usage_and_example,
        test_dry_run_reports_todo_deprecated_and_only_plan_write,
        test_actual_run_injects_missing_stable_ids_but_does_not_touch_todo_file,
        test_invalid_selected_id_returns_error,
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
