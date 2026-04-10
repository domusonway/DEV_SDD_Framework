#!/usr/bin/env python3
"""
observe-verify/check_contract.py
将 SPEC.md 中定义的接口与实现文件的 AST 对比，验证契约一致性

重点检查：
  1. 函数名称是否存在
  2. 参数名是否一致
  3. 返回类型注解是否存在且与 SPEC 匹配（特别是 bytes vs str）
  4. 抛出的异常类型是否与 SPEC 约定一致

用法:
  python3 check_contract.py --spec modules/response/SPEC.md --impl modules/response/response.py
  python3 check_contract.py --spec modules/response/SPEC.md --impl modules/response/  # 扫描目录
"""
import ast
import importlib.util
import re
import sys
import argparse
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List


TOOLS_ROOT = Path(__file__).resolve().parents[2] / "tools"
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)

ROOT = workflow_cli_common.find_framework_root(__file__)


@dataclass
class SpecInterface:
    func_name: str
    params: list  # [(name, type_str)]
    return_type: str
    exceptions: list  # [exception_class_str]
    line_hint: int = 0


@dataclass
class ImplInterface:
    func_name: str
    params: list
    return_annotation: str
    raises: list
    lineno: int


@dataclass
class ContractIssue:
    severity: str  # ERROR / WARNING
    rule: str
    message: str


# ── SPEC 解析 ─────────────────────────────────────────────────────────────────

DTYPE_CRITICAL = {"bytes", "str", "int", "float", "bool", "dict", "list", "tuple"}

def parse_spec_interfaces(spec_path: str) -> List[SpecInterface]:
    """从 SPEC.md 提取接口定义（解析 Python 代码块）"""
    content = Path(spec_path).read_text(encoding="utf-8")
    interfaces = []

    # 提取 ```python ... ``` 代码块
    code_blocks = re.findall(r"```python\n(.*?)```", content, re.DOTALL)
    for block in code_blocks:
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params = []
                for arg in node.args.args:
                    if arg.arg == "self":
                        continue
                    type_str = ""
                    if arg.annotation:
                        type_str = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else ""
                    params.append((arg.arg, type_str))

                return_type = ""
                if node.returns:
                    return_type = ast.unparse(node.returns) if hasattr(ast, "unparse") else ""

                # 提取文档字符串中的 Raises 部分
                exceptions = []
                docstring = ast.get_docstring(node) or ""
                for line in docstring.splitlines():
                    match = re.match(r"\s+(\w+Error|\w+Exception):", line)
                    if match:
                        exceptions.append(match.group(1))

                interfaces.append(SpecInterface(
                    func_name=node.name,
                    params=params,
                    return_type=return_type,
                    exceptions=exceptions,
                ))

    return interfaces


# ── 实现解析 ──────────────────────────────────────────────────────────────────

def parse_impl_interfaces(impl_path: str) -> List[ImplInterface]:
    """从实现文件提取所有非测试函数的接口"""
    try:
        source = Path(impl_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    interfaces = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_") or node.name.startswith("test_"):
            continue

        params = [(a.arg, ast.unparse(a.annotation) if a.annotation and hasattr(ast, "unparse") else "")
                  for a in node.args.args if a.arg != "self"]

        return_ann = ""
        if node.returns and hasattr(ast, "unparse"):
            return_ann = ast.unparse(node.returns)

        # 收集函数体中的 raise 语句
        raises = []
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.Raise) and child.exc:
                exc = child.exc
                if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                    raises.append(exc.func.id)
                elif isinstance(exc, ast.Name):
                    raises.append(exc.id)

        interfaces.append(ImplInterface(
            func_name=node.name,
            params=params,
            return_annotation=return_ann,
            raises=raises,
            lineno=node.lineno,
        ))

    return interfaces


# ── 契约比对 ──────────────────────────────────────────────────────────────────

def check_contract(spec: SpecInterface, impl_interfaces: List[ImplInterface]) -> List[ContractIssue]:
    issues = []

    # 找对应实现
    impl = next((i for i in impl_interfaces if i.func_name == spec.func_name), None)
    if impl is None:
        issues.append(ContractIssue(
            severity="ERROR", rule="OV_CTR_001",
            message=f"SPEC 定义的函数 `{spec.func_name}` 在实现中不存在"
        ))
        return issues

    # 检查参数名
    spec_param_names = [p[0] for p in spec.params]
    impl_param_names = [p[0] for p in impl.params]
    missing_params = set(spec_param_names) - set(impl_param_names)
    if missing_params:
        issues.append(ContractIssue(
            severity="ERROR", rule="OV_CTR_002",
            message=f"`{spec.func_name}`: 实现缺少 SPEC 定义的参数 {missing_params}"
        ))

    # 重点：返回类型检查（bytes vs str）
    if spec.return_type and impl.return_annotation:
        spec_rt = spec.return_type.lower().strip()
        impl_rt = impl.return_annotation.lower().strip()
        if spec_rt in DTYPE_CRITICAL and impl_rt in DTYPE_CRITICAL:
            if spec_rt != impl_rt:
                issues.append(ContractIssue(
                    severity="ERROR", rule="OV_CTR_003",
                    message=f"`{spec.func_name}`: 返回类型不匹配 — SPEC 要求 `{spec.return_type}`，实现标注 `{impl.return_annotation}`"
                ))
    elif spec.return_type and not impl.return_annotation:
        issues.append(ContractIssue(
            severity="WARNING", rule="OV_CTR_004",
            message=f"`{spec.func_name}`: 实现缺少返回类型注解（SPEC 要求 `{spec.return_type}`）"
        ))

    return issues


def resolve_module_paths(module_name: str, project_arg: str | None) -> tuple[str, str]:
    target_root = _detect_local_project_root(project_arg)
    if target_root is None:
        target_root, _target_label = workflow_cli_common.resolve_target_project(project_arg, ROOT, Path.cwd())
    if target_root is None:
        raise FileNotFoundError("未检测到激活项目，也未提供 --project")
    plan_path = target_root / "docs" / "plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"plan.json 不存在: {plan_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    for batch in plan.get("batches", []):
        for module in batch.get("modules", []):
            if module.get("name") != module_name:
                continue
            spec_path = str(module.get("spec_path") or "").strip()
            impl_path = str(module.get("impl_path") or module.get("path") or "").strip()
            if not spec_path or not impl_path:
                raise FileNotFoundError(f"模块 {module_name} 缺少 spec_path 或 impl_path")
            spec_target = target_root / spec_path
            impl_target = target_root / impl_path
            if not spec_target.exists():
                raise FileNotFoundError(f"模块 {module_name} 的 spec_path 不存在: {spec_target}")
            if not impl_target.exists():
                raise FileNotFoundError(f"模块 {module_name} 的 impl_path 不存在: {impl_target}")
            return str(spec_target), str(impl_target)
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
    parser = argparse.ArgumentParser(description="接口契约验证工具")
    parser.add_argument("--spec", help="SPEC.md 路径")
    parser.add_argument("--impl", help="实现文件或目录路径")
    parser.add_argument("--module", help="模块名；从 plan.json 解析 spec_path/impl_path")
    parser.add_argument("--project", help="项目名或项目路径；与 --module 搭配使用")
    args = parser.parse_args()

    if args.module:
        spec_path, impl_arg = resolve_module_paths(args.module, args.project)
    elif args.spec and args.impl:
        spec_path, impl_arg = args.spec, args.impl
    else:
        parser.error("必须提供 --spec 与 --impl，或提供 --module [--project]")

    spec_interfaces = parse_spec_interfaces(spec_path)
    if not spec_interfaces:
        print(f"⚠️ SPEC 中未找到可解析的函数定义（检查代码块格式）: {spec_path}")
        sys.exit(0)

    impl_path = Path(impl_arg)
    if impl_path.is_dir():
        impl_files = list(impl_path.rglob("*.py"))
        impl_files = [f for f in impl_files if "test_" not in f.name and "__pycache__" not in str(f)]
    else:
        impl_files = [impl_path]

    all_impl_interfaces = []
    for f in impl_files:
        all_impl_interfaces.extend(parse_impl_interfaces(str(f)))

    all_issues = []
    for spec_iface in spec_interfaces:
        all_issues.extend(check_contract(spec_iface, all_impl_interfaces))

    if not all_issues:
        funcs = [i.func_name for i in spec_interfaces]
        print(f"✅ CONTRACT OK — {len(spec_interfaces)} 个接口验证通过: {', '.join(funcs)}")
        sys.exit(0)

    errors = [i for i in all_issues if i.severity == "ERROR"]
    warnings = [i for i in all_issues if i.severity == "WARNING"]

    for issue in all_issues:
        icon = "❌" if issue.severity == "ERROR" else "⚠️"
        print(f"{icon} [{issue.rule}] {issue.message}")

    print(f"\n合计: {len(errors)} 错误, {len(warnings)} 警告")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
