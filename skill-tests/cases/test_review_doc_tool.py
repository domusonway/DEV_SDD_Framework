#!/usr/bin/env python3
"""
skill-tests/cases/test_review_doc_tool.py
Layer 1: /DEV_SDD:review_doc 辅助 CLI 合规测试

用途:
  验证 .claude/tools/review-doc/run.py 的接口与审查行为：
  - 语法与 --help 章节
  - --json 输出 schema: {status,message,data}
  - 完整 SPEC 可判定为通过
  - 缺失/薄弱 SPEC 能输出可操作的 warning
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/review-doc/run.py"
CMD_PATH = FRAMEWORK_ROOT / ".claude/commands/dev-sdd-review-doc.md"


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


def _mk_project(name: str, inside_projects: bool = True) -> Path:
    if inside_projects:
        base_dir = FRAMEWORK_ROOT / "projects"
        project_root = Path(tempfile.mkdtemp(prefix=f"{name}_", dir=str(base_dir)))
    else:
        project_root = Path(tempfile.mkdtemp(prefix=f"{name}_"))
    (project_root / "docs").mkdir(parents=True, exist_ok=True)
    (project_root / "modules").mkdir(parents=True, exist_ok=True)
    (project_root / "memory").mkdir(parents=True, exist_ok=True)
    (project_root / "memory" / "sessions").mkdir(parents=True, exist_ok=True)
    (project_root / "CLAUDE.md").write_text("# test\n工作模式: M 标准\n", encoding="utf-8")
    (project_root / "memory" / "INDEX.md").write_text("# mem\n", encoding="utf-8")
    return project_root


def _write_context(project_root: Path, modules: list[dict[str, str]]):
    lines = [
        "# Demo Review Context",
        "",
        "## INIT 结构化补充",
        "",
        "## 模块划分",
        "",
    ]
    for module in modules:
        lines.extend([
            f"### {module['name']}",
            f"- 职责: {module['职责']}",
            f"- 输入: {module['输入']}",
            f"- 输出: {module['输出']}",
            f"- 依赖: {module['依赖']}",
            "",
        ])
    (project_root / "docs" / "CONTEXT.md").write_text("\n".join(lines), encoding="utf-8")


def _write_spec(project_root: Path, module_name: str, content: str):
    spec_dir = project_root / "modules" / module_name
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "SPEC.md").write_text(content, encoding="utf-8")


def test_tool_and_command_exist_and_syntax_ok():
    assert TOOL_PATH.exists(), f"run.py 不存在: {TOOL_PATH}"
    assert CMD_PATH.exists(), f"命令文档不存在: {CMD_PATH}"
    res = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert res.returncode == 0, f"run.py 语法错误: {res.stderr}"


def test_help_contains_usage_and_example():
    res = run_tool("--help")
    out = res.stdout + res.stderr
    assert "用途" in out, "--help 缺少「用途」"
    assert "示例" in out or "example" in out.lower(), "--help 缺少「示例」"


def test_complete_spec_passes_review():
    project_root = _mk_project("review_doc_ok")
    try:
        _write_context(project_root, [
            {
                "name": "alpha",
                "职责": "读取 harness.yaml 和 cases.json 生成校验报告",
                "输入": "harness.yaml, cases.json",
                "输出": "校验报告, Case 列表",
                "依赖": "models",
            }
        ])
        _write_spec(
            project_root,
            "alpha",
            """# SPEC: alpha

## 模块职责

alpha 负责读取 harness.yaml 和 cases.json，产出校验报告与 Case 列表，供后续流程消费。

## 覆盖范围

- 输入包含 harness.yaml 与 cases.json
- 输出包含校验报告与 Case 列表
- 依赖 models 中的基础类型

## 依赖

- 依赖模块: models
- 被依赖: cli

## 类型契约

```python
def load_alpha(harness_yaml: str, cases_index: str) -> list[dict[str, object]]: ...
```

## 精确规则

| 对象 | 字段 | 约束 |
|------|------|------|
| 输入 | harness.yaml | 必须存在且可解析 |
| 输入 | cases.json | 必须存在且可解析 |
| 输出 | 校验报告 | 必须包含错误计数 |
| 输出 | Case 列表 | 必须保持原顺序 |

## 行为规格

- 正常路径: 读取 harness.yaml 与 cases.json，返回 Case 列表和校验报告。
- 边界情况: 空 cases.json 返回空列表，但仍生成校验报告。
- 错误路径: 缺少 harness.yaml 或 cases.json 时抛 ValueError，错误消息必须包含文件名。

## TDD 测试最小集合

- 成功读取 harness.yaml 与 cases.json
- 空 Case 列表仍产生校验报告
- 缺少 cases.json 时返回可定位的错误
""",
        )

        res = run_tool(str(project_root), "--json")
        assert res.returncode == 0, f"review_doc 成功场景失败: {res.stderr}"
        data = parse_json_output(res, "review_doc ok")
        assert data["status"] == "ok", f"完整 SPEC 应通过: {data}"
        assert data["data"]["summary"]["warning_modules"] == 0
        module = data["data"]["modules"][0]
        assert module["module"] == "alpha"
        assert module["coverage"]["covered"] is True
        assert module["quality"]["specific"] is True
        assert module["quality"]["rigorous"] is True
        assert module["quality"]["executable"] is True
    finally:
        shutil.rmtree(project_root, ignore_errors=True)


def test_missing_and_weak_specs_report_warnings():
    project_root = _mk_project("review_doc_warn", inside_projects=False)
    try:
        _write_context(project_root, [
            {
                "name": "alpha",
                "职责": "读取 harness.yaml 和 cases.json 生成校验报告",
                "输入": "harness.yaml, cases.json",
                "输出": "校验报告, Case 列表",
                "依赖": "models",
            },
            {
                "name": "beta",
                "职责": "汇总评分结果生成终端输出",
                "输入": "scores.db, filter 参数",
                "输出": "终端输出, CSV 文件",
                "依赖": "storage",
            },
        ])
        _write_spec(
            project_root,
            "alpha",
            """# SPEC: alpha

## 模块职责

alpha 负责处理数据。

## 行为规格

- 正常路径: 返回结果
""",
        )
        _write_spec(
            project_root,
            "gamma",
            """# SPEC: gamma

## 模块职责

额外模块。
""",
        )

        res = run_tool(str(project_root), "--json")
        assert res.returncode == 0, f"review_doc warning 场景失败: {res.stderr}"
        data = parse_json_output(res, "review_doc warning")
        assert data["status"] == "warning", f"存在缺口时应返回 warning: {data}"
        assert data["data"]["summary"]["warning_modules"] == 2

        modules = {item["module"]: item for item in data["data"]["modules"]}
        assert "beta" in modules
        beta_issue_kinds = {issue["kind"] for issue in modules["beta"]["issues"]}
        assert "missing_spec" in beta_issue_kinds, f"beta 应标记缺失 SPEC: {modules['beta']}"

        alpha = modules["alpha"]
        assert alpha["coverage"]["covered"] is False, "弱 SPEC 应出现覆盖缺口"
        assert alpha["quality"]["specific"] is False, "弱 SPEC 应被判定为不够具体"
        assert alpha["quality"]["rigorous"] is False, "弱 SPEC 应被判定为不够严谨"
        assert alpha["quality"]["executable"] is False, "弱 SPEC 应被判定为不够可执行"
        assert data["data"]["orphan_specs"] == ["modules/gamma/SPEC.md"], "应报告 CONTEXT 未声明的额外 SPEC"
    finally:
        shutil.rmtree(project_root, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_tool_and_command_exist_and_syntax_ok,
        test_help_contains_usage_and_example,
        test_complete_spec_passes_review,
        test_missing_and_weak_specs_report_warnings,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
        except AssertionError as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__} [ERROR]: {e}")
            failed += 1
    print(f"\n{'─' * 50}")
    print(f"  {len(tests) - failed}/{len(tests)} 通过")
    sys.exit(failed)
