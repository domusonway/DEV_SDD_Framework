#!/usr/bin/env python3
from __future__ import annotations

"""
observe-verify/check_impl.py
检查 Python 实现文件是否存在不完整的占位符（pass, return None, raise NotImplementedError）

用法: python3 check_impl.py <file_or_directory>
"""
import ast
import importlib.util
import sys
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List


TOOLS_ROOT = Path(__file__).resolve().parents[2] / "tools"
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)

ROOT = workflow_cli_common.find_framework_root(__file__)


@dataclass
class Issue:
    file: str
    line: int
    func: str
    severity: str  # ERROR / WARNING
    rule: str
    message: str


def is_stub_body(body: list) -> bool:
    """判断函数体是否只有占位符"""
    if not body:
        return True
    # 只有 pass
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return True
    # 只有文档字符串 + pass
    if len(body) == 2 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[1], ast.Pass):
            return True
    return False


def has_bare_return_none(body: list) -> bool:
    """函数体是否只返回 None（无逻辑）"""
    stmts = [s for s in body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
    if len(stmts) == 1 and isinstance(stmts[0], ast.Return):
        val = stmts[0].value
        if val is None or (isinstance(val, ast.Constant) and val.value is None):
            return True
    return False


def has_only_not_implemented(body: list) -> bool:
    """函数体是否只有 raise NotImplementedError"""
    stmts = [s for s in body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
    if len(stmts) == 1 and isinstance(stmts[0], ast.Raise):
        exc = stmts[0].exc
        if exc is None:
            return False
        if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
            return exc.func.id == "NotImplementedError"
        if isinstance(exc, ast.Name):
            return exc.id == "NotImplementedError"
    return False


def has_hardcoded_return(node: ast.FunctionDef, source_lines: list) -> bool:
    """检测疑似硬编码的单一返回值（不使用任何参数）"""
    params = {a.arg for a in node.args.args if a.arg != "self"}
    if not params:
        return False

    # 收集函数体中使用到的 Name 节点
    used_names = set()
    for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
        if isinstance(child, ast.Name):
            used_names.add(child.id)

    # 如果没有任何参数名出现在函数体中，可能是硬编码
    if not params.intersection(used_names):
        # 进一步确认：函数体中有 Return 语句
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.Return) and child.value is not None:
                return True
    return False


def scan_file(filepath: str) -> List[Issue]:
    issues = []
    try:
        source = Path(filepath).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=filepath)
        source_lines = source.splitlines()
    except (SyntaxError, UnicodeDecodeError) as e:
        issues.append(Issue(filepath, 0, "<file>", "ERROR", "SYNTAX", str(e)))
        return issues

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        func_name = node.name
        lineno = node.lineno

        # 跳过测试函数和 __init__ 等常见合法 pass
        if func_name.startswith("test_") or func_name in ("__init__", "__str__", "__repr__"):
            continue

        if is_stub_body(node.body):
            issues.append(Issue(
                file=filepath, line=lineno, func=func_name,
                severity="ERROR", rule="OV_IMPL_001",
                message=f"函数 `{func_name}` 体为空或只有 pass，实现未完成"
            ))
        elif has_only_not_implemented(node.body):
            issues.append(Issue(
                file=filepath, line=lineno, func=func_name,
                severity="ERROR", rule="OV_IMPL_002",
                message=f"函数 `{func_name}` 只有 raise NotImplementedError，实现未完成"
            ))
        elif has_bare_return_none(node.body):
            issues.append(Issue(
                file=filepath, line=lineno, func=func_name,
                severity="WARNING", rule="OV_IMPL_003",
                message=f"函数 `{func_name}` 只返回 None，可能是未完成的实现"
            ))
        elif has_hardcoded_return(node, source_lines):
            issues.append(Issue(
                file=filepath, line=lineno, func=func_name,
                severity="WARNING", rule="OV_IMPL_004",
                message=f"函数 `{func_name}` 未使用任何参数，可能是硬编码返回值"
            ))

    return issues


def resolve_module_impl_target(module_name: str, project_arg: str | None) -> str:
    target_root = _detect_local_project_root(project_arg)
    if target_root is None:
        target_root, _target_label = workflow_cli_common.resolve_target_project(project_arg, ROOT, Path.cwd())
    if target_root is None:
        raise FileNotFoundError("未检测到激活项目，也未提供 --project")
    plan_path = target_root / "docs" / "plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"plan.json 不存在: {plan_path}")
    import json

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    for batch in plan.get("batches", []):
        for module in batch.get("modules", []):
            if module.get("name") != module_name:
                continue
            impl_path = str(module.get("impl_path") or module.get("path") or "").strip()
            if not impl_path:
                raise FileNotFoundError(f"模块 {module_name} 缺少 impl_path")
            target = target_root / impl_path
            if not target.exists():
                raise FileNotFoundError(f"模块 {module_name} 的 impl_path 不存在: {target}")
            return str(target)
    raise FileNotFoundError(f"plan.json 中不存在模块: {module_name}")


def _detect_local_project_root(project_arg: str | None) -> Path | None:
    if project_arg:
        return None
    current = Path.cwd().resolve()
    for candidate in [current] + list(current.parents):
        if (candidate / "docs" / "plan.json").exists():
            return candidate
        claude_md = candidate / "CLAUDE.md"
        if claude_md.exists():
            project = workflow_cli_common.parse_project_from_text(workflow_cli_common.safe_read_text(claude_md))
            if project and (candidate / "projects" / project / "docs" / "plan.json").exists():
                return (candidate / "projects" / project).resolve()
    return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="实现完整性检查工具")
    parser.add_argument("target", nargs="?", help="实现文件或目录路径（兼容旧用法）")
    parser.add_argument("--module", help="模块名；从 plan.json 解析 impl_path")
    parser.add_argument("--project", help="项目名或项目路径；与 --module 搭配使用")
    args = parser.parse_args()

    if args.module:
        target = resolve_module_impl_target(args.module, args.project)
    elif args.target:
        target = args.target
    else:
        print("用法: python3 check_impl.py <file_or_directory> 或 python3 check_impl.py --module <module> [--project <project>]")
        sys.exit(1)

    all_issues: List[Issue] = []

    if os.path.isfile(target):
        files = [target]
    else:
        files = [str(p) for p in Path(target).rglob("*.py")
                 if "test_" not in p.name and "__pycache__" not in str(p)]

    for f in sorted(files):
        all_issues.extend(scan_file(f))

    if not all_issues:
        print("✅ observe-verify/check_impl: 实现完整性检查通过")
        sys.exit(0)

    errors = [i for i in all_issues if i.severity == "ERROR"]
    warnings = [i for i in all_issues if i.severity == "WARNING"]

    for issue in all_issues:
        icon = "❌" if issue.severity == "ERROR" else "⚠️"
        print(f"{icon} [{issue.rule}] {issue.file}:{issue.line} `{issue.func}` — {issue.message}")

    print(f"\n合计: {len(errors)} 错误, {len(warnings)} 警告")

    if errors:
        print("\n修复方向:")
        print("  - pass / return None → 实现真实逻辑")
        print("  - 硬编码返回值 → 使用传入参数计算结果")
        print("  - 参考 SPEC.md 的「行为规格」章节")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
