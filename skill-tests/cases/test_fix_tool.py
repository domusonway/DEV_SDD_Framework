#!/usr/bin/env python3
"""
skill-tests/cases/test_fix_tool.py
Layer 1: DEV_SDD:FIX helper CLI triage/optioning tests

用途:
  验证 .claude/tools/fix/run.py 的接口与修复分诊行为：
  - 语法与 --help 章节
  - 可复现问题时，先读取项目上下文/记忆，再输出双层修复选项
  - 稀疏问题时，低置信度降级并请求补充上下文，而不是幻觉式给出补丁
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/fix/run.py"
FIXTURES_ROOT = FRAMEWORK_ROOT / "skill-tests/fixtures/fix"


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


def build_issue_copy(source_name: str, project_root: Path) -> Path:
    source = FIXTURES_ROOT / source_name
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["project"] = str(project_root)
    issue_path = project_root.parent / source_name
    issue_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return issue_path


def assert_option_shape(option_payload):
    for field in ["summary", "files_or_modules", "risks", "regression_scope", "why"]:
        assert field in option_payload, f"修复选项缺少字段: {field}"


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"run.py 不存在: {TOOL_PATH}"
    res = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert res.returncode == 0, f"run.py 语法错误: {res.stderr}"


def test_help_contains_usage_and_example():
    res = run_tool("--help")
    out = res.stdout + res.stderr
    assert "用途" in out, "--help 缺少「用途」"
    assert "示例" in out or "example" in out.lower(), "--help 缺少「示例」"


def test_reproducible_issue_emits_dual_repair_options():
    project_root = clone_fixture("repro-project")
    issue_path = build_issue_copy("repro-issue.json", project_root)
    try:
        res = run_tool(issue_path, "--json", "--dry-run")
        assert res.returncode == 0, f"FIX dry-run 失败: {res.stderr}"
        data = parse_json_output(res, "fix repro issue")

        assert data["status"] == "ok", "可复现问题应返回 ok"
        payload = data["data"]
        assert payload.get("project") == project_root.name
        assert payload.get("plan_source") == "docs/plan.json", "应声明计划来源"
        assert payload.get("memory_source") == "memory/INDEX.md", "应先读取项目 memory"

        triage = payload.get("triage") or {}
        assert triage.get("reproducibility") == "reproducible", "应识别为可复现问题"
        assert triage.get("confidence") in {"medium", "high"}, "可复现问题不应降级为低置信度"
        assert "calibration" in (triage.get("likely_modules") or []), "应结合上下文识别相关模块"

        memory_signals = triage.get("memory_signals") or {}
        assert memory_signals.get("known_constraints"), "应汇总项目约束"
        assert memory_signals.get("known_bugs"), "应汇总已知 bug 记忆"
        assert memory_signals.get("decision_context"), "应汇总设计决策"

        options = payload.get("options") or {}
        assert list(options.keys()) == ["minimal_change", "comprehensive_change"], "应固定输出两层修复选项"
        assert_option_shape(options["minimal_change"])
        assert_option_shape(options["comprehensive_change"])
        assert "calibration" in json.dumps(options["minimal_change"], ensure_ascii=False).lower(), "最小修复应围绕定位模块"
        assert "stripe_matching" in json.dumps(options["comprehensive_change"], ensure_ascii=False).lower(), (
            "全面修复应体现下游影响与回归范围"
        )

        follow_up = payload.get("memory_follow_up") or {}
        assert "recommended" in follow_up, "应输出记忆沉淀跟进建议"
        assert follow_up.get("path") == f"projects/{project_root.name}/memory/INDEX.md"
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


def test_sparse_issue_requires_more_context():
    project_root = clone_fixture("sparse-project")
    issue_path = build_issue_copy("sparse-issue.json", project_root)
    try:
        res = run_tool(issue_path, "--json", "--dry-run")
        assert res.returncode == 0, f"FIX sparse dry-run 失败: {res.stderr}"
        data = parse_json_output(res, "fix sparse issue")

        assert data["status"] == "warning", "稀疏问题应返回 warning 降级"
        payload = data["data"]
        triage = payload.get("triage") or {}
        assert triage.get("reproducibility") == "sparse"
        assert triage.get("confidence") == "low", "缺失复现信息时应降级为低置信度"
        missing = triage.get("missing_context") or []
        for required in ["reproduction_steps", "expected_behavior", "actual_behavior"]:
            assert required in missing, f"应明确指出缺失上下文: {required}"

        options = payload.get("options") or {}
        assert list(options.keys()) == ["minimal_change", "comprehensive_change"], "降级时也应保持双层选项结构"
        assert_option_shape(options["minimal_change"])
        assert_option_shape(options["comprehensive_change"])

        minimal_text = json.dumps(options["minimal_change"], ensure_ascii=False)
        comprehensive_text = json.dumps(options["comprehensive_change"], ensure_ascii=False)
        assert "补充" in minimal_text or "上下文" in minimal_text, "最小方案应请求补充上下文"
        assert "观测" in comprehensive_text or "诊断" in comprehensive_text, "全面方案应偏向诊断/观测增强"
    finally:
        shutil.rmtree(project_root.parent, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_tool_exists_and_syntax_ok,
        test_help_contains_usage_and_example,
        test_reproducible_issue_emits_dual_repair_options,
        test_sparse_issue_requires_more_context,
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
