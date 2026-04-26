#!/usr/bin/env python3
from __future__ import annotations

"""Classify, scaffold, and validate DEV_SDD document templates."""

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

ROOT = workflow_cli_common.find_framework_root(__file__)
TEMPLATES_DIR = ROOT / "docs" / "templates"


def envelope(status: str, message: str, data: dict[str, Any], as_json: bool) -> None:
    payload = {"status": status, "message": message, "data": data}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"{status}: {message}")
    if data:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    if not content.startswith("---\n"):
        return {}, content
    end = content.find("\n---", 4)
    if end == -1:
        return {}, content
    meta_text = content[4:end].strip()
    body = content[end + 4:].lstrip("\n")
    meta: dict[str, Any] = {}
    for line in meta_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in {"intent_keywords", "required_sections"}:
            meta[key] = [item.strip() for item in re.split(r"[,，]", value) if item.strip()]
        else:
            meta[key] = value.strip("'\"")
    return meta, body


def load_templates() -> dict[str, dict[str, Any]]:
    templates: dict[str, dict[str, Any]] = {}
    for path in sorted(TEMPLATES_DIR.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        content = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        template_id = str(meta.get("id") or path.stem)
        templates[template_id] = {"id": template_id, "path": path, "meta": meta, "body": body}
    return templates


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[`*_#>\[\]()/\\:;,.，。!?？]+", "-", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "document"


def classify_text(text: str) -> dict[str, Any]:
    templates = load_templates()
    lower = text.lower()
    scored = []
    for template_id, template in templates.items():
        keywords = template["meta"].get("intent_keywords") or []
        score = 0
        matched = []
        for keyword in keywords:
            if keyword.lower() in lower:
                score += 2 if len(keyword) >= 4 else 1
                matched.append(keyword)
        if template_id == "module-validation-report" and any(term in lower for term in ["cli", "上游", "下游", "单模块", "模块"]):
            score += 3
        if template_id == "problem-analysis" and any(term in lower for term in ["根因", "报错", "失败", "bug"]):
            score += 2
        if template_id == "decision-record" and any(term in lower for term in ["取舍", "决策", "选择"]):
            score += 2
        if template_id == "architecture-overview" and any(term in lower for term in ["架构", "数据流", "模块边界", "框架梳理"]):
            score += 3
        if template_id == "rule-guide" and any(term in lower for term in ["规则", "指引", "规范", "操作指南"]):
            score += 3
        if template_id == "implementation-brief" and any(term in lower for term in ["实现", "功能", "feature", "开发"]):
            score += 2
        if template_id == "review-report" and any(term in lower for term in ["审查报告", "代码审查", "文档审查", "质量审查"]):
            score += 3
        scored.append({"template_id": template_id, "score": score, "matched_keywords": matched})
    scored = sorted(scored, key=lambda item: (-int(item["score"]), item["template_id"]))
    best = scored[0] if scored else {"template_id": "problem-analysis", "score": 0, "matched_keywords": []}
    score = int(best["score"])
    confidence = "high" if score >= 5 else ("medium" if score >= 2 else "low")
    template = templates.get(str(best["template_id"]), {})
    language_policy = str(template.get("meta", {}).get("language_policy") or "zh_cn_default_preserve_terms")
    return {
        "query": text,
        "template_id": best["template_id"],
        "confidence": confidence,
        "language_policy": language_policy,
        "matched_keywords": best["matched_keywords"],
        "candidates": scored[:5],
    }


def resolve_project(project: str | None) -> tuple[Path | None, str | None]:
    return workflow_cli_common.resolve_target_project(project, ROOT)


def render_template(template: dict[str, Any], project: str | None, module: str | None, topic: str | None, title: str | None) -> tuple[str, str]:
    meta = template["meta"]
    project_root, project_label = resolve_project(project)
    project_label = project_label or "PROJECT"
    module_label = module or "module"
    topic_label = slugify(topic or module_label or template["id"])
    filename_pattern = str(meta.get("filename_pattern") or f"{template['id']}.md")
    filename = filename_pattern.replace("<module>", slugify(module_label)).replace("<topic>", topic_label).replace("<PROJECT>", project_label)
    default_dir = str(meta.get("default_dir") or "docs")
    default_dir = default_dir.replace("<PROJECT>", project_label).replace("<module>", slugify(module_label)).replace("<topic>", topic_label)
    suggested_path = workflow_cli_common.rel_path((ROOT / default_dir / filename).resolve(), ROOT)
    doc_title = title or f"{module_label} · {template['id']}" if module else template["id"]
    body = template["body"]
    replacements = {
        "<TITLE>": doc_title,
        "<PROJECT>": project_label,
        "<MODULE>": module_label,
        "<CODE_PATH>": f"projects/{project_label}/modules/**/{module_label}",
        "<SPEC_PATH>": f"projects/{project_label}/modules/**/{module_label}/SPEC.md",
    }
    for key, value in replacements.items():
        body = body.replace(key, value)
    return suggested_path, body


def extract_headings(content: str) -> set[str]:
    headings = set()
    for line in content.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            headings.add(match.group(1).strip())
    return headings


def validate_doc(path: Path, template_id: str) -> dict[str, Any]:
    templates = load_templates()
    if template_id not in templates:
        return {"template_id": template_id, "valid": False, "missing_sections": [], "issues": [f"unknown template: {template_id}"]}
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    required = templates[template_id]["meta"].get("required_sections") or []
    headings = extract_headings(content)
    missing = [section for section in required if section not in headings]
    issues = []
    if not path.exists():
        issues.append("document does not exist")
    if missing:
        issues.append(f"missing required sections: {', '.join(missing)}")
    return {
        "template_id": template_id,
        "path": workflow_cli_common.rel_path(path, ROOT),
        "valid": not missing and path.exists(),
        "required_sections": required,
        "present_sections": sorted(headings),
        "missing_sections": missing,
        "issues": issues,
    }


def command_classify(args: argparse.Namespace) -> int:
    text = " ".join(args.text).strip()
    data = classify_text(text)
    envelope("ok", f"classified as {data['template_id']}", data, args.json)
    return 0


def command_list(args: argparse.Namespace) -> int:
    templates = load_templates()
    data = {"templates": [{"id": tid, "path": workflow_cli_common.rel_path(t["path"], ROOT), "meta": t["meta"]} for tid, t in templates.items()]}
    envelope("ok", f"{len(templates)} templates", data, args.json)
    return 0


def command_scaffold(args: argparse.Namespace) -> int:
    templates = load_templates()
    if args.template_id not in templates:
        envelope("error", f"unknown template: {args.template_id}", {"available": sorted(templates)}, args.json)
        return 1
    suggested_path, content = render_template(templates[args.template_id], args.project, args.module, args.topic, args.title)
    output_path = ROOT / suggested_path
    language_policy = str(templates[args.template_id]["meta"].get("language_policy") or "zh_cn_default_preserve_terms")
    data = {"template_id": args.template_id, "suggested_path": suggested_path, "language_policy": language_policy, "content": content, "written": False}
    if args.write:
        if output_path.exists() and not args.overwrite:
            envelope("error", f"target exists: {suggested_path}", data, args.json)
            return 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        data["written"] = True
    envelope("ok", f"scaffolded {args.template_id}", data, args.json)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    template_id = args.template or classify_text(Path(args.path).name)["template_id"]
    path = Path(args.path)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    data = validate_doc(path, template_id)
    status = "ok" if data["valid"] else "warning"
    envelope(status, "document template validation complete", data, args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DEV_SDD doc-template helper")
    sub = parser.add_subparsers(dest="command", required=True)

    classify = sub.add_parser("classify")
    classify.add_argument("text", nargs="+")
    classify.add_argument("--json", action="store_true")
    classify.set_defaults(func=command_classify)

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--json", action="store_true")
    list_cmd.set_defaults(func=command_list)

    scaffold = sub.add_parser("scaffold")
    scaffold.add_argument("template_id")
    scaffold.add_argument("--project", default=None)
    scaffold.add_argument("--module", default=None)
    scaffold.add_argument("--topic", default=None)
    scaffold.add_argument("--title", default=None)
    scaffold.add_argument("--write", action="store_true")
    scaffold.add_argument("--overwrite", action="store_true")
    scaffold.add_argument("--json", action="store_true")
    scaffold.set_defaults(func=command_scaffold)

    validate = sub.add_parser("validate")
    validate.add_argument("path")
    validate.add_argument("--template", default=None)
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=command_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
