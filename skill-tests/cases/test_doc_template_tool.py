#!/usr/bin/env python3
from __future__ import annotations

"""Layer 1: doc-template skill/tool tests."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/doc-template/run.py"
SKILL_PATH = FRAMEWORK_ROOT / ".claude/skills/doc-template/SKILL.md"
TEMPLATES_DIR = FRAMEWORK_ROOT / "docs/templates"
STANDARD_SUB_DOCS_DIRS = ["analysis", "architecture", "bug", "decisions", "feature", "reports", "rules", "validation"]
REQUIRED_TEMPLATES = [
    "problem-analysis",
    "architecture-overview",
    "project-status-review",
    "module-validation-report",
    "decision-record",
    "implementation-brief",
    "rule-guide",
    "review-report",
]


def run_tool(*args: str):
    return subprocess.run([sys.executable, str(TOOL_PATH), *args], capture_output=True, text=True, cwd=str(FRAMEWORK_ROOT))


def parse_json(result, label: str):
    assert result.stdout.strip(), f"{label} 无输出"
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"status", "message", "data"}
    assert payload["status"] in {"ok", "warning", "error"}
    return payload


def test_skill_templates_and_tool_exist():
    assert SKILL_PATH.exists(), "doc-template skill 不存在"
    assert TOOL_PATH.exists(), "doc-template tool 不存在"
    for template_id in REQUIRED_TEMPLATES:
        path = TEMPLATES_DIR / f"{template_id}.md"
        assert path.exists(), f"模板缺失: {path}"
        content = path.read_text(encoding="utf-8")
        assert "required_sections:" in content
        assert "filename_pattern:" in content
        assert "language_policy: zh_cn_default_preserve_terms" in content
    result = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    skill = SKILL_PATH.read_text(encoding="utf-8")
    assert "[DOC-TEMPLATE]" in skill
    assert "template_id:" in skill
    assert "target_path:" in skill
    assert "language:" in skill
    assert "默认尽可能使用中文" in skill


def test_standard_sub_docs_directories_exist_and_map_to_templates():
    roots = [
        FRAMEWORK_ROOT / "docs/sub_docs",
        FRAMEWORK_ROOT / "projects/_template/docs/sub_docs",
        FRAMEWORK_ROOT / "projects/agentplatform/docs/sub_docs",
    ]
    for root in roots:
        assert (root / "README.md").exists(), f"sub_docs README 缺失: {root}"
        readme = (root / "README.md").read_text(encoding="utf-8")
        for dirname in STANDARD_SUB_DOCS_DIRS:
            assert (root / dirname / "README.md").exists(), f"标准目录或 README 缺失: {root / dirname}"
            assert f"`{dirname}/`" in readme, f"README 未声明标准目录 {dirname}: {root}"
    index = (TEMPLATES_DIR / "INDEX.md").read_text(encoding="utf-8")
    for dirname in STANDARD_SUB_DOCS_DIRS:
        assert f"`{dirname}/`" in index, f"templates INDEX 缺少目录映射: {dirname}"


def test_classify_selects_module_validation_template():
    result = run_tool("classify", "从 CLI、模型上游和下游输出验证 runtime 单模块功能流程性能", "--json")
    assert result.returncode == 0, result.stderr
    data = parse_json(result, "classify")["data"]
    assert data["template_id"] == "module-validation-report", data
    assert data["confidence"] in {"high", "medium"}
    assert data["language_policy"] == "zh_cn_default_preserve_terms"


def test_scaffold_returns_project_sub_doc_path_and_required_sections():
    result = run_tool("scaffold", "module-validation-report", "--project", "agentplatform", "--module", "runtime", "--json")
    assert result.returncode == 0, result.stderr
    data = parse_json(result, "scaffold")["data"]
    assert data["template_id"] == "module-validation-report"
    assert data["suggested_path"].endswith("projects/agentplatform/docs/sub_docs/validation/runtime-validation-report.md")
    assert data["language_policy"] == "zh_cn_default_preserve_terms"
    content = data["content"]
    for heading in ["## 验证目标", "## 入口路径", "## 上游输入", "## 下游输出", "## 执行命令", "## 详细证据"]:
        assert heading in content


def test_new_template_classification_and_paths_are_standardized():
    cases = [
        ("梳理模块边界和数据流", "architecture-overview", "/docs/sub_docs/architecture/"),
        ("写一个操作规则指引", "rule-guide", "/docs/sub_docs/rules/"),
        ("创建功能实现方案", "implementation-brief", "/docs/sub_docs/feature/"),
        ("输出质量审查报告", "review-report", "/docs/sub_docs/reports/"),
    ]
    for text, template_id, path_part in cases:
        classified = parse_json(run_tool("classify", text, "--json"), f"classify {template_id}")["data"]
        assert classified["template_id"] == template_id, classified
        scaffold = parse_json(run_tool("scaffold", template_id, "--project", "agentplatform", "--topic", "demo", "--json"), f"scaffold {template_id}")["data"]
        assert path_part in scaffold["suggested_path"], scaffold["suggested_path"]


def test_validate_reports_missing_required_sections():
    temp_dir = Path(tempfile.mkdtemp(prefix="doc_template_validate_"))
    try:
        doc = temp_dir / "weak.md"
        doc.write_text("# Weak\n\n## 摘要\n\n只有摘要。\n", encoding="utf-8")
        result = run_tool("validate", str(doc), "--template", "module-validation-report", "--json")
        assert result.returncode == 0, result.stderr
        payload = parse_json(result, "validate weak")
        assert payload["status"] == "warning"
        missing = payload["data"]["missing_sections"]
        assert "验证目标" in missing
        assert "执行命令" in missing
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_scaffold_write_refuses_to_overwrite_without_flag():
    temp_project = Path(tempfile.mkdtemp(prefix="doc_template_project_", dir=str(FRAMEWORK_ROOT / "projects")))
    try:
        (temp_project / "docs" / "sub_docs" / "validation").mkdir(parents=True, exist_ok=True)
        (temp_project / "CLAUDE.md").write_text("# temp\n", encoding="utf-8")
        (temp_project / "memory").mkdir(exist_ok=True)
        target = temp_project / "docs" / "sub_docs" / "validation" / "runtime-validation-report.md"
        target.write_text("existing", encoding="utf-8")
        result = run_tool("scaffold", "module-validation-report", "--project", temp_project.name, "--module", "runtime", "--write", "--json")
        payload = parse_json(result, "scaffold overwrite guard")
        assert payload["status"] == "error"
        assert "exists" in payload["message"]
        assert target.read_text(encoding="utf-8") == "existing"
    finally:
        shutil.rmtree(temp_project, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_skill_templates_and_tool_exist,
        test_standard_sub_docs_directories_exist_and_map_to_templates,
        test_classify_selects_module_validation_template,
        test_scaffold_returns_project_sub_doc_path_and_required_sections,
        test_new_template_classification_and_paths_are_standardized,
        test_validate_reports_missing_required_sections,
        test_scaffold_write_refuses_to_overwrite_without_flag,
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
    sys.exit(failed)
