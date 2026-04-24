#!/usr/bin/env python3
"""
skill-tests/cases/test_redefine_tool.py
Layer 1: DEV_SDD:REDEFINE helper CLI 合规测试

用途:
  验证 .claude/tools/redefine/run.py 的接口与重定义传播行为：
  - 语法与 --help 章节
  - 计划重定义传播顺序（先更新 plan.json，再生成派生文档）
  - 兼容别名 REDEFIND，不引入分叉语义路径
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


FRAMEWORK_ROOT = Path(__file__).parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/redefine/run.py"
FIXTURES_ROOT = FRAMEWORK_ROOT / "skill-tests/fixtures/redefine"


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


def _module_states(plan: dict[str, Any]):
    return {
        module["name"]: module.get("state", "pending")
        for batch in plan.get("batches", [])
        for module in batch.get("modules", [])
    }


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"run.py 不存在: {TOOL_PATH}"
    res = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert res.returncode == 0, f"run.py 语法错误: {res.stderr}"


def test_help_contains_usage_and_example():
    res = run_tool("--help")
    out = res.stdout + res.stderr
    assert "用途" in out, "--help 缺少「用途」"
    assert "示例" in out or "example" in out.lower(), "--help 缺少「示例」"


def test_propagates_plan_updates_and_regenerates_derived_docs():
    project_root = clone_fixture("plan-change-project")
    try:
        dry_run = run_tool(project_root, "--json", "--dry-run")
        assert dry_run.returncode == 0, f"dry-run 失败: {dry_run.stderr}"
        preview = parse_json_output(dry_run, "redefine dry-run")
        assert preview["status"] == "ok", "重定义 dry-run 应成功"
        data = preview["data"]
        assert data.get("plan_source") == "docs/plan.json", "应声明 plan.json 为执行真相源"
        assert data.get("input_source") == "docs/CONTEXT.md", "上游输入应来自项目 CONTEXT"
        writes = data.get("writes", [])
        write_paths = [item["path"] for item in writes]
        assert write_paths[:2] == ["docs/plan.json", "docs/PLAN.md"], (
            f"传播顺序应先 plan.json 后 PLAN.md: {write_paths}"
        )
        changes = data.get("changes", {})
        assert "redefine_flow" in changes.get("added_modules", []), "应识别新增模块"
        assert "legacy_sync" in changes.get("removed_modules", []), "应识别移除模块"
        assert "capture_context" in changes.get("preserved_modules", []), "应识别保留模块"

        before_plan = json.loads((project_root / "docs/plan.json").read_text(encoding="utf-8"))
        assert "legacy_sync" in _module_states(before_plan), "fixture 前置条件异常：缺少 legacy_sync"

        actual = run_tool(project_root, "--json")
        assert actual.returncode == 0, f"实际重定义失败: {actual.stderr}"
        result = parse_json_output(actual, "redefine actual")
        assert result["status"] == "ok", "重定义实际执行应成功"

        plan = json.loads((project_root / "docs/plan.json").read_text(encoding="utf-8"))
        states = _module_states(plan)
        assert set(states.keys()) == {"capture_context", "redefine_flow"}, f"plan.json 应按新规划重建: {states}"
        assert states["capture_context"] == "completed", "重定义应保留未变模块已有执行状态"
        assert states["redefine_flow"] == "pending", "新增模块应默认为 pending"

        plan_md = (project_root / "docs/PLAN.md").read_text(encoding="utf-8")
        assert "redefine_flow" in plan_md and "legacy_sync" not in plan_md, "PLAN.md 应由新 plan.json 派生"
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


def test_legacy_alias_redefind_routes_to_same_semantics():
    project_root = clone_fixture("plan-change-project")
    try:
        alias = run_tool("--alias", "REDEFIND", project_root, "--json", "--dry-run")
        assert alias.returncode == 0, f"REDEFIND alias 执行失败: {alias.stderr}"
        data = parse_json_output(alias, "redefine alias")
        assert data["status"] == "ok", "REDEFIND alias 应成功复用 REDEFINE 语义"
        alias_meta = data["data"].get("alias") or {}
        assert alias_meta.get("used") is True, "alias 元数据应标记已启用兼容别名"
        assert alias_meta.get("name") == "REDEFIND", "alias 元数据应记录原始别名"
        assert "REDEFIND" in data["message"], "返回消息应包含 alias 兼容提示"

        writes = [item["path"] for item in data["data"].get("writes", [])]
        assert writes[:2] == ["docs/plan.json", "docs/PLAN.md"]
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_tool_exists_and_syntax_ok,
        test_help_contains_usage_and_example,
        test_propagates_plan_updates_and_regenerates_derived_docs,
        test_legacy_alias_redefind_routes_to_same_semantics,
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
