#!/usr/bin/env python3
"""
skill-tests/cases/test_init_tool.py
Layer 1: DEV_SDD:INIT helper CLI 合规测试

用途:
  验证 .claude/tools/init/run.py 的接口与初始化保护行为：
  - 语法与 --help 章节
  - 空项目 bootstrap 的 dry-run 与实际输出
  - 现有文档冲突时返回 confirmation metadata 而不是静默覆盖
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/init/run.py"
FIXTURES_ROOT = FRAMEWORK_ROOT / "skill-tests/fixtures/init"


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


def test_bootstrap_empty_project_creates_authoritative_plan_and_docs():
    project_root = clone_fixture("empty-project")
    try:
        dry_run = run_tool(project_root, "--json", "--dry-run")
        assert dry_run.returncode == 0, f"dry-run 失败: {dry_run.stderr}"
        preview = parse_json_output(dry_run, "init bootstrap dry-run")
        assert preview["status"] == "ok", "空项目 dry-run 应成功"
        assert preview["data"].get("dry_run") is True, "dry-run 标志应回传"
        planned = {item["path"] for item in preview["data"].get("writes", [])}
        assert {
            "CLAUDE.md",
            "AGENTS.md",
            "README.md",
            "docs/plan.json",
            "docs/PLAN.md",
            "docs/TODO.md",
        }.issubset(planned), f"缺少预期初始化目标: {planned}"
        assert not (project_root / "CLAUDE.md").exists(), "dry-run 不应实际写入 CLAUDE.md"
        assert not (project_root / "docs/plan.json").exists(), "dry-run 不应实际写入 plan.json"

        actual = run_tool(project_root, "--json")
        assert actual.returncode == 0, f"实际初始化失败: {actual.stderr}"
        result = parse_json_output(actual, "init bootstrap actual")
        assert result["status"] == "ok", "空项目 bootstrap 应成功"
        assert (project_root / "CLAUDE.md").exists(), "应生成 CLAUDE.md"
        assert (project_root / "AGENTS.md").exists(), "应生成 AGENTS.md"
        assert (project_root / "README.md").exists(), "应生成 README.md"
        assert (project_root / "docs/plan.json").exists(), "应生成 plan.json"
        assert (project_root / "docs/PLAN.md").exists(), "应生成 PLAN.md"
        assert (project_root / "docs/TODO.md").exists(), "应生成 TODO.md"

        plan = json.loads((project_root / "docs/plan.json").read_text(encoding="utf-8"))
        assert plan["project"] == "Demo Init Project", "plan.json 应从 CONTEXT 标题派生项目名"
        module_names = [m["name"] for batch in plan.get("batches", []) for m in batch.get("modules", [])]
        assert module_names == ["capture_context", "build_plan"], "plan.json 应从模块划分生成模块清单"

        claude = (project_root / "CLAUDE.md").read_text(encoding="utf-8")
        assert "docs/plan.json" in claude, "CLAUDE.md 应声明 plan.json 为权威状态"
        readme = (project_root / "README.md").read_text(encoding="utf-8")
        assert "建立一个最小 DEV_SDD 初始化样例" in readme, "README 应包含 CONTEXT 中的项目目标"
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


def test_existing_docs_require_confirmation_and_preserve_files():
    project_root = clone_fixture("existing-docs-project")
    try:
        original_claude = (project_root / "CLAUDE.md").read_text(encoding="utf-8")
        original_plan = (project_root / "docs/plan.json").read_text(encoding="utf-8")

        res = run_tool(project_root, "--json", "--dry-run")
        assert res.returncode == 0, f"overwrite guard dry-run 不应崩溃: {res.stderr}"
        data = parse_json_output(res, "init overwrite guard")
        assert data["status"] == "warning", "存在冲突时应返回 warning"
        confirmation = data["data"].get("confirmation") or {}
        assert confirmation.get("required") is True, "应明确要求确认"
        conflicts = {item["path"] for item in confirmation.get("conflicts", [])}
        assert {"CLAUDE.md", "README.md", "docs/PLAN.md", "docs/TODO.md", "docs/plan.json"}.issubset(conflicts), (
            f"应列出需要确认的冲突文件: {conflicts}"
        )
        assert confirmation.get("diff_preview"), "应返回差异预览元数据"

        no_confirm = run_tool(project_root, "--json")
        result = parse_json_output(no_confirm, "init overwrite guard actual")
        assert result["status"] == "warning", "未确认前实际运行也应拒绝覆盖"
        assert (project_root / "CLAUDE.md").read_text(encoding="utf-8") == original_claude, "CLAUDE.md 不应被静默覆盖"
        assert (project_root / "docs/plan.json").read_text(encoding="utf-8") == original_plan, "plan.json 不应被静默覆盖"
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


def test_repo_relative_project_path_does_not_duplicate_projects_segment():
    res = run_tool("projects/does-not-exist", "--json")
    assert res.returncode == 1, "缺失 CONTEXT 的显式 repo-relative 路径应返回 error"
    data = parse_json_output(res, "init repo-relative missing project")
    assert data["status"] == "error", "缺失项目目录时应返回 error"
    project_root = data["data"].get("project_root", "")
    assert project_root.endswith("projects/does-not-exist"), f"project_root 应保持 repo-relative 解析: {project_root}"
    assert "projects/projects/does-not-exist" not in project_root, f"project_root 不应重复 projects 段: {project_root}"


if __name__ == "__main__":
    tests = [
        test_tool_exists_and_syntax_ok,
        test_help_contains_usage_and_example,
        test_bootstrap_empty_project_creates_authoritative_plan_and_docs,
        test_existing_docs_require_confirmation_and_preserve_files,
        test_repo_relative_project_path_does_not_duplicate_projects_segment,
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
