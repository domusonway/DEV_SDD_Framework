#!/usr/bin/env python3
"""
review-doc/run.py

用途:
  /DEV_SDD:review_doc 的执行辅助 CLI。
  审查项目 docs/CONTEXT.md 中的模块功能定义，确认其是否被 modules/**/SPEC.md 覆盖，
  并评估 SPEC 是否足够具体、严谨、可执行。

用法:
  python3 .claude/tools/review-doc/run.py [project-name-or-path] [--json]

示例:
  python3 .claude/tools/review-doc/run.py
  python3 .claude/tools/review-doc/run.py HarnessEvaluationFramework --json
  python3 .claude/tools/review-doc/run.py projects/HarnessEvaluationFramework
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)


STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"

FIELD_ORDER = ["职责", "输入", "输出", "依赖"]

GENERIC_TERMS = {
    "负责",
    "模块",
    "用于",
    "管理",
    "定义",
    "处理",
    "相关",
    "结果",
    "信息",
    "数据",
    "记录",
    "配置",
    "集合",
    "列表",
    "文件",
    "目录",
    "对象",
    "服务",
    "生成",
    "提供",
    "统一",
    "当前",
    "用户",
}


def out(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    status_val = str(payload.get("status") or "")
    icon = {STATUS_OK: "✅", STATUS_WARNING: "⚠️", STATUS_ERROR: "❌"}.get(status_val, "ℹ️")
    print(f"{icon}  {payload.get('message', '')}")
    data = payload.get("data") or {}
    summary = data.get("summary") or {}
    print("[REVIEW_DOC]")
    print(f"项目: {data.get('project', 'unknown')}")
    print(f"CONTEXT: {data.get('context_source', 'missing')}")
    print(
        "总结: "
        f"总模块 {summary.get('total_modules', 0)} | "
        f"通过 {summary.get('passed_modules', 0)} | "
        f"告警 {summary.get('warning_modules', 0)} | "
        f"缺失SPEC {summary.get('missing_specs', 0)}"
    )
    for module in data.get("modules", []):
        print(f"- {module.get('module')}: {module.get('status')}")
        for issue in module.get("issues", []):
            print(f"  - {issue.get('kind')}: {issue.get('detail')}")
    orphan_specs = data.get("orphan_specs") or []
    if orphan_specs:
        print(f"额外SPEC: {', '.join(orphan_specs)}")
    print("[/REVIEW_DOC]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "用途:\n"
            "  审查项目 docs/CONTEXT.md 的模块定义是否被 modules/**/SPEC.md 覆盖，\n"
            "  并评估 SPEC 是否足够具体、严谨、可执行。\n\n"
            "示例:\n"
            "  python3 .claude/tools/review-doc/run.py\n"
            "  python3 .claude/tools/review-doc/run.py HarnessEvaluationFramework --json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("target", nargs="?", help="project name or project path")
    parser.add_argument("--json", action="store_true", help="output structured JSON")
    return parser


def find_framework_root() -> Path:
    return workflow_cli_common.find_framework_root(__file__)


ROOT = find_framework_root()


def safe_read_text(path: Path) -> str:
    return workflow_cli_common.safe_read_text(path)


def rel_path(path: Path, base: Path) -> str:
    return workflow_cli_common.rel_path(path, base)


def detect_active_project(root: Path) -> str | None:
    return workflow_cli_common.detect_active_project(root)


def resolve_target(target_arg: str | None, base_dir: Path | None = None) -> tuple[Path | None, str | None]:
    return workflow_cli_common.resolve_target_project(target_arg, ROOT, base_dir=base_dir)


def parse_markdown_sections(content: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    for line in content.splitlines():
        match = re.match(r"^##\s+(.+)$", line)
        if match:
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = match.group(1).strip()
            buffer = []
            continue
        if current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def parse_context_modules(context_text: str) -> tuple[list[dict[str, Any]], str | None]:
    sections = parse_markdown_sections(context_text)
    modules_block = sections.get("模块划分")
    if not modules_block:
        return [], "docs/CONTEXT.md 缺少 `## 模块划分` 机器可读区块"

    modules: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in modules_block.splitlines():
        heading = re.match(r"^###\s+(.+)$", line.strip())
        if heading:
            if current is not None:
                modules.append(current)
            current = {"module": heading.group(1).strip(), "fields": {}}
            continue
        field = re.match(r"^-\s*(职责|输入|输出|依赖):\s*(.+)$", line.strip())
        if field and current is not None:
            current["fields"][field.group(1)] = field.group(2).strip()
    if current is not None:
        modules.append(current)

    return modules, None if modules else "`## 模块划分` 未解析出任何模块"


def list_spec_files(project_root: Path) -> dict[str, list[Path]]:
    spec_map: dict[str, list[Path]] = {}
    for spec_path in sorted(project_root.glob("modules/**/SPEC.md")):
        module_name = spec_path.parent.name
        spec_map.setdefault(module_name, []).append(spec_path)
    return spec_map


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def keyword_tokens(text: str) -> list[str]:
    raw_tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_./*-]*|[\u4e00-\u9fff]{2,}", text.lower())
    tokens: list[str] = []
    for token in raw_tokens:
        cleaned = token.strip("`.,:;()[]{}<>!?")
        if not cleaned or cleaned in GENERIC_TERMS:
            continue
        tokens.append(cleaned)
        if "/" in cleaned:
            for part in cleaned.split("/"):
                part = part.strip("*.-_")
                if len(part) >= 2 and part not in GENERIC_TERMS:
                    tokens.append(part)
    return tokens


def split_expected_items(value: str) -> list[str]:
    parts = re.split(r"[、,，;；]|\s+/\s+|\s+and\s+", value)
    results: list[str] = []
    for part in parts:
        cleaned = part.strip().strip("`")
        if cleaned:
            results.append(cleaned)
    return results or [value.strip()]


def item_covered(item: str, spec_text: str) -> bool:
    lowered = normalize_text(spec_text)
    tokens = keyword_tokens(item)
    if not tokens:
        return True
    matched = [token for token in tokens if token in lowered]
    code_like = [token for token in tokens if re.search(r"[a-z0-9_.]", token)]
    code_like_matched = [token for token in code_like if token in lowered]
    if code_like and code_like_matched:
        return True
    if len(tokens) <= 2:
        return bool(matched)
    return len(matched) >= max(2, len(tokens) // 2)


def extract_section_by_keyword(sections: dict[str, str], keyword: str) -> str:
    for heading, body in sections.items():
        if keyword in heading:
            return body
    return ""


def evaluate_coverage(module_fields: dict[str, str], spec_text: str, sections: dict[str, str]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    missing_fields: list[str] = []
    field_details: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []

    dependency_text = extract_section_by_keyword(sections, "依赖") or spec_text
    for field_name in FIELD_ORDER:
        expected = str(module_fields.get(field_name) or "").strip()
        if not expected:
            missing_fields.append(field_name)
            issues.append({"kind": "context_field_missing", "detail": f"CONTEXT 缺少 `{field_name}` 描述"})
            continue

        missing_items: list[str] = []
        if field_name == "依赖":
            expected_items = split_expected_items(expected)
            if expected_items == ["无"]:
                if "无" not in dependency_text and "依赖模块: 无" not in dependency_text:
                    missing_items = expected_items
            else:
                for item in expected_items:
                    if not item_covered(item, dependency_text):
                        missing_items.append(item)
        else:
            for item in split_expected_items(expected):
                if not item_covered(item, spec_text):
                    missing_items.append(item)

        if missing_items:
            missing_fields.append(field_name)
            field_details.append({"field": field_name, "missing_items": missing_items})
            issues.append({
                "kind": "coverage_gap",
                "detail": f"`{field_name}` 未覆盖: {', '.join(missing_items)}",
            })

    return {
        "covered": not missing_fields,
        "missing_fields": missing_fields,
        "field_details": field_details,
    }, issues


def evaluate_quality(spec_text: str, sections: dict[str, str]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    headings = list(sections.keys())
    heading_text = "\n".join(headings)
    lowered = normalize_text(spec_text)
    signals = {
        "has_interface": any(keyword in heading_text for keyword in ["接口", "类型契约", "数据结构", "契约"]),
        "has_behavior": any(keyword in heading_text for keyword in ["行为", "覆盖范围", "职责", "规则"]),
        "has_rules": any(keyword in heading_text for keyword in ["精确规则", "约束", "边界", "错误"]),
        "has_tests": any(keyword in heading_text for keyword in ["测试", "TDD", "验收"]),
        "has_code_block": "```" in spec_text,
        "has_table": bool(re.search(r"^\|.+\|\s*$", spec_text, re.MULTILINE)),
        "has_must": "必须" in spec_text,
        "has_explicit_error": "错误消息必须包含" in spec_text,
        "char_count": len(spec_text.strip()),
        "constraint_signal": bool(re.search(r"\[\s*0\s*,\s*1\s*\]|>=|<=|仅允许|literal\[", lowered)),
    }

    quality = {
        "specific": signals["char_count"] >= 300 and signals["has_behavior"] and (
            signals["has_interface"] or signals["has_code_block"] or signals["has_table"]
        ),
        "rigorous": (signals["has_rules"] or signals["has_must"]) and (
            signals["has_table"] or signals["has_explicit_error"] or signals["constraint_signal"]
        ),
        "executable": signals["has_tests"] and (signals["has_interface"] or signals["has_behavior"]),
        "signals": signals,
    }

    issues: list[dict[str, str]] = []
    if not quality["specific"]:
        issues.append({
            "kind": "quality_gap",
            "detail": "SPEC 不够具体，缺少明确接口/类型/行为信号或正文过短",
        })
    if not quality["rigorous"]:
        issues.append({
            "kind": "quality_gap",
            "detail": "SPEC 不够严谨，缺少约束、边界、错误路径或精确规则",
        })
    if not quality["executable"]:
        issues.append({
            "kind": "quality_gap",
            "detail": "SPEC 不够可执行，缺少测试最小集合、TDD 线索或验收标准",
        })
    return quality, issues


def review_module(module_entry: dict[str, Any], spec_paths: list[Path], project_root: Path) -> dict[str, Any]:
    module_name = str(module_entry.get("module") or "")
    fields = dict(module_entry.get("fields") or {})

    result = {
        "module": module_name,
        "status": STATUS_OK,
        "context": fields,
        "spec_path": None,
        "coverage": {"covered": False, "missing_fields": FIELD_ORDER, "field_details": []},
        "quality": {"specific": False, "rigorous": False, "executable": False, "signals": {}},
        "issues": [],
    }

    if not spec_paths:
        result["status"] = STATUS_WARNING
        result["issues"].append({"kind": "missing_spec", "detail": "未找到对应的 SPEC.md"})
        return result

    if len(spec_paths) > 1:
        result["status"] = STATUS_WARNING
        result["issues"].append({
            "kind": "duplicate_spec",
            "detail": "存在多个同名 SPEC: " + ", ".join(rel_path(path, project_root) for path in spec_paths),
        })

    spec_path = spec_paths[0]
    spec_text = safe_read_text(spec_path)
    result["spec_path"] = rel_path(spec_path, project_root)

    if not spec_text.strip():
        result["status"] = STATUS_WARNING
        result["issues"].append({"kind": "empty_spec", "detail": "SPEC 文件为空或无法读取"})
        return result

    sections = parse_markdown_sections(spec_text)
    coverage, coverage_issues = evaluate_coverage(fields, spec_text, sections)
    quality, quality_issues = evaluate_quality(spec_text, sections)
    result["coverage"] = coverage
    result["quality"] = quality
    result["issues"].extend(coverage_issues)
    result["issues"].extend(quality_issues)

    if result["issues"]:
        result["status"] = STATUS_WARNING
    return result


def build_payload(target_arg: str | None, base_dir: Path | None = None) -> tuple[dict[str, Any], int]:
    project_root, label = resolve_target(target_arg, base_dir=base_dir)
    if project_root is None:
        payload = {
            "status": STATUS_WARNING,
            "message": "未检测到激活项目，无法执行 REVIEW_DOC",
            "data": {
                "project": None,
                "next_action": "提供项目名或项目路径，或先激活项目后重试",
            },
        }
        return payload, 0

    if not project_root.exists():
        payload = {
            "status": STATUS_ERROR,
            "message": f"目标项目不存在: {project_root}",
            "data": {
                "project": label,
                "project_root": str(project_root),
            },
        }
        return payload, 1

    context_path = project_root / "docs" / "CONTEXT.md"
    context_text = safe_read_text(context_path)
    if not context_text.strip():
        payload = {
            "status": STATUS_ERROR,
            "message": "缺少 docs/CONTEXT.md，无法执行 REVIEW_DOC",
            "data": {
                "project": label or project_root.name,
                "project_root": str(project_root),
                "context_source": rel_path(context_path, project_root),
            },
        }
        return payload, 1

    context_modules, parse_error = parse_context_modules(context_text)
    if parse_error:
        payload = {
            "status": STATUS_ERROR,
            "message": f"无法解析 CONTEXT 模块划分: {parse_error}",
            "data": {
                "project": label or project_root.name,
                "project_root": str(project_root),
                "context_source": rel_path(context_path, project_root),
            },
        }
        return payload, 1

    spec_map = list_spec_files(project_root)
    modules = [review_module(entry, spec_map.get(str(entry.get("module") or ""), []), project_root) for entry in context_modules]

    context_names = {str(entry.get("module") or "") for entry in context_modules}
    orphan_specs = sorted(
        rel_path(paths[0], project_root)
        for name, paths in spec_map.items()
        if name not in context_names and paths
    )

    passed_modules = sum(1 for item in modules if item["status"] == STATUS_OK)
    warning_modules = sum(1 for item in modules if item["status"] == STATUS_WARNING)
    missing_specs = sum(1 for item in modules if any(issue["kind"] == "missing_spec" for issue in item["issues"]))

    status = STATUS_OK if warning_modules == 0 and not orphan_specs else STATUS_WARNING
    payload = {
        "status": status,
        "message": (
            f"REVIEW_DOC 完成：{len(modules)} 个模块中 {warning_modules} 个存在覆盖或质量缺口"
            if status == STATUS_WARNING
            else f"REVIEW_DOC 完成：{len(modules)} 个模块的 SPEC 覆盖与质量检查通过"
        ),
        "data": {
            "project": label or project_root.name,
            "project_root": str(project_root),
            "context_source": rel_path(context_path, project_root),
            "summary": {
                "total_modules": len(modules),
                "passed_modules": passed_modules,
                "warning_modules": warning_modules,
                "missing_specs": missing_specs,
            },
            "modules": modules,
            "orphan_specs": orphan_specs,
        },
    }
    return payload, 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload, code = build_payload(args.target)
    out(payload, args.json)
    return code


if __name__ == "__main__":
    sys.exit(main())
