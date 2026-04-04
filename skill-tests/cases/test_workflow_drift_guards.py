#!/usr/bin/env python3
"""
skill-tests/cases/test_workflow_drift_guards.py
Layer 1: workflow drift regression guards

用途:
  固化历史审计结论，防止以下回归漂移：
  - 根文档重新出现未解析占位符（{{ / }}）
  - root docs/PLAN.md 退回 markdown-first 叙述，弱化 plan.json 权威性
  - UPDATE_TODO 在本地托管区冲突时未确认就覆盖
  - workflow helper 共享契约测试从 Layer 1 注册中漂移
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).parent.parent.parent
DOCS_ROOT = FRAMEWORK_ROOT / "docs"
RUN_ALL_PATH = FRAMEWORK_ROOT / "skill-tests/run_all.py"
UPDATE_TODO_TOOL = FRAMEWORK_ROOT / ".claude/tools/update-todo/run.py"
UPDATE_TODO_FIXTURES = FRAMEWORK_ROOT / "skill-tests/fixtures/update_todo"
WORKFLOW_CONTRACT_CASE = FRAMEWORK_ROOT / "skill-tests/cases/test_workflow_cli_contracts.py"


def run_update_todo(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(UPDATE_TODO_TOOL)] + [str(arg) for arg in args],
        capture_output=True,
        text=True,
        cwd=str(cwd or FRAMEWORK_ROOT),
    )


def parse_json_output(result, name):
    assert result.stdout.strip(), f"{name} 无输出"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        assert False, f"{name} 输出不是合法 JSON: {exc}\n{result.stdout[:200]}"
    assert "status" in payload, f"{name} 缺少 status"
    assert "message" in payload, f"{name} 缺少 message"
    assert "data" in payload, f"{name} 缺少 data"
    return payload


def clone_fixture(name: str) -> Path:
    source = UPDATE_TODO_FIXTURES / name
    assert source.exists(), f"fixture 不存在: {source}"
    temp_dir = Path(tempfile.mkdtemp(prefix=f"{name}_"))
    target = temp_dir / name
    shutil.copytree(source, target)
    return target


def test_root_docs_do_not_contain_unresolved_placeholders():
    root_docs = [
        DOCS_ROOT / "CONTEXT.md",
        DOCS_ROOT / "PLAN.md",
        DOCS_ROOT / "TODO.md",
    ]
    for doc in root_docs:
        text = doc.read_text(encoding="utf-8")
        assert "{{" not in text, f"{doc.relative_to(FRAMEWORK_ROOT)} 包含未解析占位符 '{{{{'"
        assert "}}" not in text, f"{doc.relative_to(FRAMEWORK_ROOT)} 包含未解析占位符 '}}}}'"


def test_root_plan_doc_keeps_plan_json_as_authoritative_source_of_truth():
    content = (DOCS_ROOT / "PLAN.md").read_text(encoding="utf-8")

    must_have = [
        "For active project work, `plan.json` is the **source of truth** and the authoritative execution plan.",
        "generated markdown may summarize status for humans, but it must not override structured state",
        "Current planning precedence is:",
        "1. `plan.json`",
        "2. `PLAN.md`",
        "3. `IMPLEMENTATION_PLAN.md`",
    ]
    for fragment in must_have:
        assert fragment in content, f"docs/PLAN.md 缺少关键防漂移语义: {fragment}"


def test_update_todo_requires_confirmation_before_overwriting_local_managed_edit():
    project_root = clone_fixture("conflict-project")
    try:
        todo_path = project_root / "docs/TODO.md"
        original = todo_path.read_text(encoding="utf-8")

        dry_run = run_update_todo(project_root, "--ids", "T-003", "--json", "--dry-run")
        assert dry_run.returncode == 0, f"conflict dry-run 失败: {dry_run.stderr}"
        preview = parse_json_output(dry_run, "update-todo drift guard dry-run")
        assert preview["status"] == "warning", "冲突场景 dry-run 应返回 warning"

        confirmation = (preview.get("data") or {}).get("confirmation") or {}
        assert confirmation.get("required") is True, "冲突场景必须要求确认"
        token = confirmation.get("token")
        assert token, "冲突场景必须返回确认 token"

        blocked = run_update_todo(project_root, "--ids", "T-003", "--json")
        blocked_payload = parse_json_output(blocked, "update-todo drift guard blocked")
        assert blocked_payload["status"] == "warning", "未确认时应阻止覆盖"
        assert todo_path.read_text(encoding="utf-8") == original, "未确认时 TODO 内容必须保持不变"

        wrong_token = run_update_todo(project_root, "--ids", "T-003", "--json", "--confirm-overwrite", "deadbeef0000")
        wrong_payload = parse_json_output(wrong_token, "update-todo drift guard wrong token")
        assert wrong_payload["status"] == "warning", "错误 token 不应允许覆盖"
        assert todo_path.read_text(encoding="utf-8") == original, "错误 token 下 TODO 不应被覆盖"

        confirmed = run_update_todo(project_root, "--ids", "T-003", "--json", "--confirm-overwrite", token)
        confirmed_payload = parse_json_output(confirmed, "update-todo drift guard confirmed")
        assert confirmed_payload["status"] == "ok", "确认 token 正确后应允许覆盖"
        assert "- [x] module_gamma <!-- DEV_SDD:TASK:id=T-003;name=module_gamma;state=completed -->" in todo_path.read_text(
            encoding="utf-8"
        )
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


def test_workflow_contract_coverage_is_registered_and_asserts_shared_envelope_rules():
    run_all = RUN_ALL_PATH.read_text(encoding="utf-8")
    assert '"test_workflow_cli_contracts.py"' in run_all, "Layer 1 注册中缺少 workflow_cli_contracts"
    assert '"test_update_todo_tool.py"' in run_all, "Layer 1 注册中缺少 update_todo 工具测试"
    assert '"test_start_work_tool.py"' in run_all, "Layer 1 注册中缺少 start_work 工具测试"

    contract_case = WORKFLOW_CONTRACT_CASE.read_text(encoding="utf-8")
    assert 'set(payload.keys()) == {"status", "message", "data"}' in contract_case, "共享 envelope 断言缺失"
    assert "test_repo_relative_project_resolution_is_stable_across_working_directories" in contract_case, (
        "缺少 cwd 稳定性回归断言"
    )


if __name__ == "__main__":
    tests = [
        test_root_docs_do_not_contain_unresolved_placeholders,
        test_root_plan_doc_keeps_plan_json_as_authoritative_source_of_truth,
        test_update_todo_requires_confirmation_before_overwriting_local_managed_edit,
        test_workflow_contract_coverage_is_registered_and_asserts_shared_envelope_rules,
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
    print(f"\n{'─' * 50}")
    print(f"  {len(tests) - failed}/{len(tests)} 通过")
    sys.exit(failed)
