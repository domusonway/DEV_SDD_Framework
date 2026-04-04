#!/usr/bin/env python3
"""
skill-tests/cases/test_update_todo_tool.py
Layer 1: DEV_SDD:UPDATE_TODO helper CLI 合规测试

用途:
  验证 .claude/tools/update-todo/run.py 的接口与稳定 ID 合并行为：
  - 语法与 --help 章节
  - 按 stable ID 进行部分更新，且保留未选中内容与用户备注区
  - 本地冲突编辑返回 confirmation metadata，禁止静默覆盖
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


def extract_notes_zone(todo_text: str) -> str:
    begin = "<!-- DEV_SDD:USER_NOTES:BEGIN -->"
    end = "<!-- DEV_SDD:USER_NOTES:END -->"
    assert begin in todo_text and end in todo_text, "TODO 缺少用户备注区标记"
    start = todo_text.index(begin)
    finish = todo_text.index(end) + len(end)
    return todo_text[start:finish]


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"run.py 不存在: {TOOL_PATH}"
    res = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert res.returncode == 0, f"run.py 语法错误: {res.stderr}"


def test_help_contains_usage_and_example():
    res = run_tool("--help")
    out = res.stdout + res.stderr
    assert "用途" in out, "--help 缺少「用途」"
    assert "示例" in out or "example" in out.lower(), "--help 缺少「示例」"


def test_partial_merge_by_id_updates_only_selected_and_preserves_notes():
    project_root = clone_fixture("partial-merge-project")
    try:
        todo_path = project_root / "docs/TODO.md"
        original_todo = todo_path.read_text(encoding="utf-8")
        original_notes = extract_notes_zone(original_todo)

        preview_res = run_tool(project_root, "--ids", "T-002,T-004", "--json", "--dry-run")
        assert preview_res.returncode == 0, f"partial merge dry-run 失败: {preview_res.stderr}"
        preview = parse_json_output(preview_res, "update-todo partial dry-run")
        assert preview["status"] == "ok", "无冲突的部分更新 dry-run 应成功"
        assert preview["data"].get("plan_source") == "docs/plan.json"
        assert preview["data"].get("todo_path") == "docs/TODO.md"
        assert preview["data"].get("selected_ids") == ["T-002", "T-004"], "应回传指定的 stable IDs"
        assert preview["data"].get("dry_run") is True

        actual_res = run_tool(project_root, "--ids", "T-002,T-004", "--json")
        assert actual_res.returncode == 0, f"partial merge 实际执行失败: {actual_res.stderr}"
        result = parse_json_output(actual_res, "update-todo partial actual")
        assert result["status"] == "ok"

        updated_todo = todo_path.read_text(encoding="utf-8")
        assert extract_notes_zone(updated_todo) == original_notes, "用户备注区应按字节保持不变"

        assert "- [x] module_beta <!-- DEV_SDD:TASK:id=T-002;name=module_beta;state=completed -->" in updated_todo
        assert "- [>] module_delta <!-- DEV_SDD:TASK:id=T-004;name=module_delta;state=in_progress -->" in updated_todo
        assert "- [ ] module_gamma (manual pin) <!-- DEV_SDD:TASK:id=T-003;name=module_gamma;state=pending -->" in updated_todo, (
            "未选中的手工编辑项不应被改写"
        )

        plan = json.loads((project_root / "docs/plan.json").read_text(encoding="utf-8"))
        module_ids = {
            module["name"]: module.get("id")
            for batch in plan.get("batches", [])
            for module in batch.get("modules", [])
        }
        assert module_ids.get("module_delta") == "T-004", "缺失 ID 的任务应被注入并持久化到 plan.json"
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


def test_conflicting_edit_requires_confirmation_metadata():
    project_root = clone_fixture("conflict-project")
    try:
        todo_path = project_root / "docs/TODO.md"
        original = todo_path.read_text(encoding="utf-8")

        dry_run = run_tool(project_root, "--ids", "T-003", "--json", "--dry-run")
        assert dry_run.returncode == 0, f"conflict dry-run 不应崩溃: {dry_run.stderr}"
        data = parse_json_output(dry_run, "update-todo conflict dry-run")
        assert data["status"] == "warning", "本地冲突编辑应返回 warning"
        confirmation = data["data"].get("confirmation") or {}
        assert confirmation.get("required") is True, "冲突时必须要求确认"
        token = confirmation.get("token")
        assert token, "冲突时必须返回确认 token"
        conflicts = confirmation.get("conflicts") or []
        assert any(item.get("id") == "T-003" and item.get("reason") == "local_managed_edit" for item in conflicts), (
            f"应返回 T-003 本地编辑冲突详情: {conflicts}"
        )

        no_confirm = run_tool(project_root, "--ids", "T-003", "--json")
        blocked = parse_json_output(no_confirm, "update-todo conflict actual")
        assert blocked["status"] == "warning", "未确认前应拒绝覆盖"
        assert todo_path.read_text(encoding="utf-8") == original, "未确认前 TODO 不应被覆盖"

        confirmed = run_tool(project_root, "--ids", "T-003", "--json", "--confirm-overwrite", token)
        confirmed_data = parse_json_output(confirmed, "update-todo conflict confirmed")
        assert confirmed_data["status"] == "ok", "确认后应允许覆盖冲突项"
        updated = todo_path.read_text(encoding="utf-8")
        assert "- [x] module_gamma <!-- DEV_SDD:TASK:id=T-003;name=module_gamma;state=completed -->" in updated
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


def test_no_op_update_by_id_keeps_todo_unchanged():
    project_root = clone_fixture("partial-merge-project")
    try:
        todo_path = project_root / "docs/TODO.md"
        original_todo = todo_path.read_text(encoding="utf-8")
        original_notes = extract_notes_zone(original_todo)

        dry_run = run_tool(project_root, "--ids", "T-001", "--json", "--dry-run")
        assert dry_run.returncode == 0, f"no-op dry-run 失败: {dry_run.stderr}"
        preview = parse_json_output(dry_run, "update-todo no-op dry-run")
        assert preview["status"] == "ok", "no-op dry-run 应成功"
        assert preview["data"].get("selected_ids") == ["T-001"], "应回传 no-op 目标 stable ID"
        writes = {item["path"]: item["action"] for item in preview["data"].get("writes", [])}
        assert writes.get("docs/TODO.md") == "maintain", "no-op 应声明 TODO 为 maintain"

        actual = run_tool(project_root, "--ids", "T-001", "--json")
        assert actual.returncode == 0, f"no-op 实际执行失败: {actual.stderr}"
        result = parse_json_output(actual, "update-todo no-op actual")
        assert result["status"] == "ok", "no-op 实际执行应成功"
        assert result["data"].get("selected_ids") == ["T-001"], "实际执行也应回传 no-op 目标 stable ID"

        after_todo = todo_path.read_text(encoding="utf-8")
        assert extract_notes_zone(after_todo) == original_notes, "no-op 场景下用户备注区应保持不变"
        assert after_todo == original_todo, "no-op 实际执行不应改动 TODO 文件内容"
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_tool_exists_and_syntax_ok,
        test_help_contains_usage_and_example,
        test_partial_merge_by_id_updates_only_selected_and_preserves_notes,
        test_conflicting_edit_requires_confirmation_metadata,
        test_no_op_update_by_id_keeps_todo_unchanged,
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
