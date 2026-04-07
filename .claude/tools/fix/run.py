#!/usr/bin/env python3
"""
fix/run.py

用途:
  /DEV_SDD:fix 的执行辅助 CLI。
  读取 issue JSON、项目上下文与项目记忆，先生成 triage 摘要，
  再输出 minimal_change / comprehensive_change 两层修复选项。

用法:
  python3 .claude/tools/fix/run.py <issue-json-path> [--json] [--dry-run]

示例:
  python3 .claude/tools/fix/run.py skill-tests/fixtures/fix/repro-issue.json --json --dry-run
  python3 .claude/tools/fix/run.py skill-tests/fixtures/fix/sparse-issue.json --json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
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


def out(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    status_val = str(payload.get("status") or "")
    icon = {STATUS_OK: "✅", STATUS_WARNING: "⚠️", STATUS_ERROR: "❌"}.get(status_val, "ℹ️")
    print(f"{icon}  {payload.get('message', '')}")
    data = payload.get("data") or {}
    triage = data.get("triage") or {}
    options = data.get("options") or {}

    print("[FIX]")
    print(f"项目: {data.get('project', 'unknown')}")
    print(f"issue: {data.get('issue_source', 'unknown')}")
    print(f"confidence: {triage.get('confidence', 'unknown')}")
    print(f"reproducibility: {triage.get('reproducibility', 'unknown')}")
    print(f"triage: {triage.get('summary', '无')}")
    # 环境状态
    env_info = data.get('environment', {})
    if env_info:
        env_status = env_info.get('status', 'unknown')
        env_icon = {"not_found": "📁", "exists_not_activated": "🔧", "activated": "🟢"}.get(env_status, "❓")
        print(f"环境: {env_icon} {env_info.get('detail', '')}")
    for name in ["minimal_change", "comprehensive_change"]:
        option = options.get(name) or {}
        print(f"{name}: {option.get('summary', '无')}")
    print("[/FIX]")


def find_framework_root() -> Path:
    return workflow_cli_common.find_framework_root(__file__)


ROOT = find_framework_root()


def safe_read_text(path: Path) -> str:
    return workflow_cli_common.safe_read_text(path)


def rel_path(path: Path, base: Path) -> str:
    return workflow_cli_common.rel_path(path, base)


def parse_project_from_text(content: str) -> str | None:
    if not content:
        return None
    match = re.search(r"^PROJECT:\s*(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def detect_active_project(root: Path) -> str | None:
    return workflow_cli_common.detect_active_project(root)


def resolve_target(target_arg: str | None, base_dir: Path | None = None) -> tuple[Path, str | None]:
    resolved, label = workflow_cli_common.resolve_target_project(target_arg, ROOT, base_dir=base_dir)
    return resolved or ROOT, label


@dataclass
class PlanResult:
    source: str
    summary: str
    next_action: str
    progress: dict[str, Any]
    nodes: list[dict[str, str]]


def _compute_next_action_from_batches(plan: dict[str, Any]) -> str:
    for batch in plan.get("batches", []):
        for module in batch.get("modules", []):
            state = module.get("state", "pending")
            if state in {"pending", "in_progress"}:
                return f"实现 {module.get('name', 'unknown')}（{batch.get('name', 'unknown')}）"
    return "所有模块已完成，可进入 validate-output"


def _load_plan_json(path: Path) -> PlanResult | None:
    if not path.exists():
        return None
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return PlanResult(
            source="plan.json",
            summary="plan.json 存在但解析失败",
            next_action="修复 docs/plan.json 的 JSON 格式错误",
            progress={"completed": 0, "in_progress": 0, "pending": 0, "total": 0, "percent": 0},
            nodes=[],
        )

    all_modules = [m for b in plan.get("batches", []) for m in b.get("modules", [])]
    total = len(all_modules)
    completed = sum(1 for m in all_modules if m.get("state") == "completed")
    in_progress = sum(1 for m in all_modules if m.get("state") == "in_progress")
    pending = sum(1 for m in all_modules if m.get("state", "pending") == "pending")
    percent = round(completed / total * 100) if total else 0
    nodes: list[dict[str, str]] = []
    for module in all_modules:
        nodes.append({
            "id": str(module.get("id") or ""),
            "name": str(module.get("name") or ""),
            "state": str(module.get("state") or "pending"),
        })
    return PlanResult(
        source="plan.json",
        summary=f"{completed}/{total} 完成（{percent}%）",
        next_action=_compute_next_action_from_batches(plan),
        progress={
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "total": total,
            "percent": percent,
        },
        nodes=nodes,
    )


def _extract_task_name(line: str) -> str:
    text = re.sub(r"^-\s*\[[ xX~>]\]\s*", "", line).strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text.strip() or "未命名任务"


def _load_plan_markdown(path: Path) -> PlanResult | None:
    if not path.exists():
        return None
    content = safe_read_text(path)
    completed_lines = re.findall(r"^-\s*\[[xX]\]\s+.+$", content, re.MULTILINE)
    pending_lines = re.findall(r"^-\s*\[\s\]\s+.+$", content, re.MULTILINE)
    active_lines = re.findall(r"^-\s*\[>\]\s+.+$", content, re.MULTILINE)
    total = len(completed_lines) + len(pending_lines) + len(active_lines)
    percent = round(len(completed_lines) / total * 100) if total else 0
    if active_lines:
        next_action = f"继续 {_extract_task_name(active_lines[0])}"
    elif pending_lines:
        next_action = f"开始 {_extract_task_name(pending_lines[0])}"
    else:
        next_action = "阅读计划文档并定义第一个可执行模块"
    return PlanResult(
        source=path.name,
        summary=f"{len(completed_lines)}/{total} 完成（{percent}%）",
        next_action=next_action,
        progress={
            "completed": len(completed_lines),
            "in_progress": len(active_lines),
            "pending": len(pending_lines),
            "total": total,
            "percent": percent,
        },
        nodes=[],
    )


def detect_plan(project_docs: Path) -> PlanResult:
    json_result = _load_plan_json(project_docs / "plan.json")
    if json_result is not None:
        return json_result

    for name in ["PLAN.md", "IMPLEMENTATION_PLAN.md"]:
        md_result = _load_plan_markdown(project_docs / name)
        if md_result is not None:
            return md_result

    return PlanResult(
        source="none",
        summary="未检测到 plan.json / PLAN.md / IMPLEMENTATION_PLAN.md",
        next_action="先补齐 CONTEXT / 计划文件，再进行 triage",
        progress={"completed": 0, "in_progress": 0, "pending": 0, "total": 0, "percent": 0},
        nodes=[],
    )


def extract_section(content: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+.+$", content[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(content)
    return content[start:end].strip()


def first_nonempty_paragraph(section: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", section) if part.strip()]
    return paragraphs[0] if paragraphs else ""


def parse_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            raw = stripped[2:].strip()
            return raw.split("·", 1)[0].strip() or fallback
    return fallback


def parse_modules(content: str) -> list[str]:
    section = extract_section(content, "模块划分")
    if not section:
        return []
    return [match.group(1).strip() for match in re.finditer(r"^###\s+(.+)$", section, re.MULTILINE)]


def parse_three_line_summary(content: str) -> list[str]:
    section = extract_section(content, "⚡ 3行摘要（切换到本项目时必读，5秒知道特有约束）")
    if not section:
        return []
    results: list[str] = []
    for line in section.splitlines():
        match = re.match(r"^\s*\d+\.\s*(.+)$", line.strip())
        if match:
            results.append(match.group(1).strip())
    return results


def parse_markdown_table(content: str, heading: str) -> list[dict[str, str]]:
    section = extract_section(content, heading)
    lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return []
    headers = [part.strip() for part in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != len(headers):
            continue
        row = {headers[i]: parts[i] for i in range(len(headers))}
        if all(value in {"", "（暂无）", "暂无"} for value in row.values()):
            continue
        rows.append(row)
    return rows


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        clean = str(item).strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
    return result


def load_issue(issue_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(issue_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"issue 文件不存在: {issue_path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"issue JSON 解析失败: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("issue 输入必须是 JSON 对象")
    return payload


def load_project_context(project_root: Path) -> dict[str, Any]:
    docs_context_path = project_root / "docs" / "CONTEXT.md"
    claude_path = project_root / "CLAUDE.md"
    readme_path = project_root / "README.md"

    docs_context = safe_read_text(docs_context_path)
    claude_text = safe_read_text(claude_path)
    readme_text = safe_read_text(readme_path)
    sources = [
        rel_path(path, ROOT)
        for path, content in [
            (docs_context_path, docs_context),
            (claude_path, claude_text),
            (readme_path, readme_text),
        ]
        if content
    ]

    title = parse_title(docs_context or claude_text or readme_text, project_root.name)
    goal = first_nonempty_paragraph(extract_section(docs_context, "项目目标"))
    if not goal:
        goal = first_nonempty_paragraph(extract_section(claude_text, "项目简介"))
    if not goal:
        goal = first_nonempty_paragraph(readme_text)

    background = first_nonempty_paragraph(extract_section(docs_context, "背景"))
    module_names = parse_modules(docs_context)
    return {
        "title": title,
        "goal": goal,
        "background": background,
        "module_names": module_names,
        "sources": sources,
    }


def check_environment_status(project_root: Path | None) -> tuple[str, str]:
    """Check if env/ directory exists and if virtual environment is activated.
    
    Returns a tuple of (status, detail) where status is one of:
    - "not_found": env/ directory does not exist
    - "exists_not_activated": env/ directory exists but venv not activated
    - "activated": project's virtual environment is currently activated
    """
    if project_root is None:
        return "not_found", "未检测到项目目录，无法检查环境"
    
    env_dir = project_root / "env"
    if not env_dir.exists():
        return "not_found", "未找到 env/ 目录，请先运行 /DEV_SDD:init 初始化项目"
    
    # 检查是否在虚拟环境中
    import sys
    import platform
    is_virtual_env = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if is_virtual_env:
        # 已经在虚拟环境中
        # 进一步检查是否是项目的env目录
        try:
            # 获取当前虚拟环境的路径
            if hasattr(sys, 'base_prefix'):
                venv_path = Path(sys.base_prefix)
            else:
                venv_path = Path(sys.prefix)
            
            # 检查是否是项目的env目录
            if venv_path.resolve() == env_dir.resolve():
                return "activated", f"已进入项目虚拟环境: {env_dir}"
            else:
                # 在其他虚拟环境中，提供切换到项目环境的指导
                system = platform.system().lower()
                if system == "windows":
                    activate_cmd = f".\\env\\Scripts\\activate"
                else:  # Linux/macOS
                    activate_cmd = f"source env/bin/activate"
                return "exists_not_activated", f"当前在其他虚拟环境中。请先退出当前环境 (deactivate)，然后执行: {activate_cmd}"
        except Exception:
            # 如果出现异常，保守地报告存在但未确认激活
            return "exists_not_activated", f"env/ 目录存在 ({env_dir})，激活状态未知。请参考 env/README.md"
    else:
        # 不在虚拟环境中，提供激活指导
        system = platform.system().lower()
        if system == "windows":
            activate_cmd = f".\\env\\Scripts\\activate"
        else:  # Linux/macOS
            activate_cmd = f"source env/bin/activate"
        return "exists_not_activated", f"env/ 目录存在但未激活。请执行: {activate_cmd}"


def load_project_memory(project_root: Path) -> dict[str, Any]:
    memory_path = project_root / "memory" / "INDEX.md"
    content = safe_read_text(memory_path)
    if not content:
        return {
            "path": None,
            "known_constraints": [],
            "bugs": [],
            "decisions": [],
        }
    return {
        "path": rel_path(memory_path, ROOT),
        "known_constraints": parse_three_line_summary(content),
        "bugs": parse_markdown_table(content, "🐛 Bug 经验表"),
        "decisions": parse_markdown_table(content, "🏗️ 设计决策表"),
    }


def derive_likely_modules(issue: dict[str, Any], context: dict[str, Any], plan: PlanResult) -> list[str]:
    hints = normalize_list(issue.get("module_hints"))
    text_blob = " ".join([
        str(issue.get("title") or ""),
        str(issue.get("summary") or ""),
        str(issue.get("expected_behavior") or ""),
        str(issue.get("actual_behavior") or ""),
        str(issue.get("suspected_impact") or ""),
        " ".join(normalize_list(issue.get("symptoms"))),
        " ".join(normalize_list(issue.get("reproduction_steps"))),
        " ".join(normalize_list(issue.get("file_hints"))),
    ]).lower()
    discovered = list(hints)
    for name in dedupe(context.get("module_names") or []):
        if name.lower() in text_blob:
            discovered.append(name)
    for node in plan.nodes:
        name = str(node.get("name") or "")
        if name and name.lower() in text_blob:
            discovered.append(name)
    return dedupe(discovered)


def derive_regression_scope(primary_modules: list[str], plan: PlanResult) -> list[str]:
    scope = list(primary_modules)
    if not primary_modules:
        return scope
    primary_set = set(primary_modules)
    for node in plan.nodes:
        name = str(node.get("name") or "")
        if not name or name in primary_set:
            continue
        for candidate in primary_set:
            if candidate in {"calibration"} and name in {"stripe_matching", "reconstruction_3d"}:
                scope.append(name)
            if candidate in {"sync_pipeline"} and name in {"export_session"}:
                scope.append(name)
    return dedupe(scope)


def summarize_bug_row(row: dict[str, str]) -> str:
    return " | ".join([
        row.get("ID", "").strip(),
        row.get("症状摘要", "").strip(),
        row.get("根因", "").strip(),
        row.get("预防规则", "").strip(),
    ]).strip(" |")


def summarize_decision_row(row: dict[str, str]) -> str:
    return " | ".join([
        row.get("决策点", "").strip(),
        row.get("选择", "").strip(),
        row.get("核心原因", "").strip(),
    ]).strip(" |")


def select_memory_signals(issue: dict[str, Any], memory: dict[str, Any], likely_modules: list[str]) -> dict[str, list[str]]:
    issue_text = " ".join([
        str(issue.get("title") or ""),
        str(issue.get("summary") or ""),
        str(issue.get("suspected_impact") or ""),
        " ".join(normalize_list(issue.get("symptoms"))),
        " ".join(normalize_list(issue.get("file_hints"))),
    ]).lower()

    matched_bugs: list[str] = []
    for row in memory.get("bugs") or []:
        summary = summarize_bug_row(row)
        haystack = summary.lower()
        if any(module.lower() in haystack for module in likely_modules) or any(token in haystack for token in issue_text.split() if len(token) > 5):
            matched_bugs.append(summary)
    if not matched_bugs:
        matched_bugs = [summarize_bug_row(row) for row in (memory.get("bugs") or [])[:2]]

    matched_decisions: list[str] = []
    for row in memory.get("decisions") or []:
        summary = summarize_decision_row(row)
        haystack = summary.lower()
        if any(module.lower() in haystack for module in likely_modules) or any(token in haystack for token in issue_text.split() if len(token) > 5):
            matched_decisions.append(summary)
    if not matched_decisions:
        matched_decisions = [summarize_decision_row(row) for row in (memory.get("decisions") or [])[:2]]

    return {
        "known_constraints": list(memory.get("known_constraints") or [])[:3],
        "known_bugs": matched_bugs[:2],
        "decision_context": matched_decisions[:2],
    }


def compute_missing_context(issue: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not normalize_list(issue.get("reproduction_steps")):
        missing.append("reproduction_steps")
    if not str(issue.get("expected_behavior") or "").strip():
        missing.append("expected_behavior")
    if not str(issue.get("actual_behavior") or "").strip():
        missing.append("actual_behavior")
    if not str(issue.get("log_excerpt") or "").strip():
        missing.append("log_excerpt")
    return missing


def determine_confidence(issue: dict[str, Any], likely_modules: list[str], missing_context: list[str]) -> tuple[str, str]:
    has_repro = "reproduction_steps" not in missing_context and "expected_behavior" not in missing_context and "actual_behavior" not in missing_context
    has_file_hints = bool(normalize_list(issue.get("file_hints")))
    if not has_repro:
        return "low", "sparse"
    if has_repro and (has_file_hints or likely_modules):
        return "high", "reproducible"
    if has_repro or likely_modules:
        return "medium", "reproducible" if has_repro else "sparse"
    return "low", "sparse"


def build_options(issue: dict[str, Any], triage: dict[str, Any], plan: PlanResult) -> dict[str, dict[str, Any]]:
    likely_modules = triage.get("likely_modules") or ["unknown"]
    file_hints = normalize_list(issue.get("file_hints"))
    regression_scope = triage.get("regression_scope") or likely_modules
    memory_signals = triage.get("memory_signals") or {}
    origin = likely_modules[0]
    issue_title = str(issue.get("title") or "该问题")
    confidence = triage.get("confidence")

    if confidence == "low":
        return {
            "minimal_change": {
                "summary": "先补齐最小复现、预期/实际行为和关键日志，再决定是否进入实现层修复；当前不承诺具体补丁。",
                "files_or_modules": likely_modules,
                "risks": [
                    "短期内不会立即消除故障现象",
                    "如果在缺少样本时直接改实现，可能制造新的同步漂移",
                ],
                "regression_scope": regression_scope,
                "why": "输入信息过 sparse；根据 diagnose-bug 的先观察后修改纪律，应先补充上下文而不是猜测修复代码。",
            },
            "comprehensive_change": {
                "summary": "建立一次完整的诊断/观测方案：采集时间戳、失败样本、最近变更范围和日志，再基于真实样本决定是否做跨模块修复。",
                "files_or_modules": regression_scope,
                "risks": [
                    "前期诊断成本更高",
                    "需要协调更多模块输出调试信息",
                ],
                "regression_scope": regression_scope,
                "why": "当前最不确定的是触发条件而不是补丁位置；先增强观测能避免幻觉式 patch 建议。",
            },
        }

    minimal_targets = dedupe(file_hints + [origin])
    comprehensive_targets = dedupe(file_hints + regression_scope)
    constraint_hint = (memory_signals.get("known_constraints") or ["修复时保持现有项目约束"])[0]
    bug_hint = (memory_signals.get("known_bugs") or ["问题根因需要在源头边界被拦住"])[0]

    return {
        "minimal_change": {
            "summary": f"在 {origin} 边界收紧输入校验，并补一条针对“{issue_title}”的定向回归，先阻断无效状态继续扩散。",
            "files_or_modules": minimal_targets,
            "risks": [
                "可能暴露此前被容忍的坏输入，影响调用方错误路径",
                "如果错误边界定义不清，局部修复可能只把异常提前而未统一错误语义",
            ],
            "regression_scope": regression_scope,
            "why": f"issue 已具备稳定复现信号；项目记忆也提示“{bug_hint}”，因此先做源头收口能最快降低回归面。",
        },
        "comprehensive_change": {
            "summary": f"把 {origin} 的校验逻辑提升为共享守卫，并审查所有依赖该输出的下游模块，统一错误语义与回归覆盖。",
            "files_or_modules": comprehensive_targets,
            "risks": [
                "改动面更大，可能触发现有测试/调用方期望调整",
                "如果共享守卫设计不当，会把局部问题扩成跨模块接口变更",
            ],
            "regression_scope": regression_scope,
            "why": f"该问题已经带有下游扩散迹象，且项目约束指出“{constraint_hint}”；全面方案更适合一次性清理共享边界。",
        },
    }


def analyze_issue(issue: dict[str, Any], project_root: Path, context: dict[str, Any], memory: dict[str, Any], plan: PlanResult) -> dict[str, Any]:
    likely_modules = derive_likely_modules(issue, context, plan)
    missing_context = compute_missing_context(issue)
    confidence, reproducibility = determine_confidence(issue, likely_modules, missing_context)
    regression_scope = derive_regression_scope(likely_modules, plan) or likely_modules or ["unknown"]
    memory_signals = select_memory_signals(issue, memory, likely_modules)

    summary_bits = []
    if context.get("goal"):
        summary_bits.append(context["goal"])
    if context.get("background"):
        summary_bits.append(context["background"])
    context_summary = " ".join(summary_bits).strip()
    if not context_summary:
        context_summary = f"项目 {project_root.name} 缺少完整上下文摘要，triage 依赖 issue 输入与 memory。"

    impact_scope = "localized"
    suspected_impact = str(issue.get("suspected_impact") or "").lower()
    if len(regression_scope) > 1 or "downstream" in suspected_impact or "下游" in suspected_impact:
        impact_scope = "localized_origin_with_downstream_risk"
    risk_level = "low" if confidence == "low" else ("high" if len(regression_scope) >= 3 else "medium")

    if confidence == "low":
        summary = "问题信息不足，先补齐最小复现与日志，再选择修复路径。"
    else:
        summary = f"问题起点更像在 {', '.join(likely_modules or ['unknown'])}，且回归面至少覆盖 {', '.join(regression_scope)}。"

    return {
        "summary": summary,
        "context_summary": context_summary,
        "reproducibility": reproducibility,
        "confidence": confidence,
        "likely_modules": likely_modules,
        "impact": {
            "scope": impact_scope,
            "risk": risk_level,
            "regression_scope": regression_scope,
        },
        "regression_scope": regression_scope,
        "missing_context": missing_context,
        "memory_signals": memory_signals,
    }


def build_memory_follow_up(project_root: Path, triage: dict[str, Any]) -> dict[str, Any]:
    confidence = triage.get("confidence")
    recommended = confidence != "low"
    if recommended:
        reason = "若本次修复沉淀出新的边界校验/回归经验，应在验证通过后更新项目 memory。"
    else:
        reason = "先补齐复现材料；只有确认根因后，新的可复用经验才值得写入 memory。"
    return {
        "recommended": recommended,
        "path": f"projects/{project_root.name}/memory/INDEX.md",
        "reason": reason,
    }


def run(issue_arg: str, dry_run: bool) -> dict[str, Any]:
    issue_path = Path(issue_arg).resolve()
    try:
        issue = load_issue(issue_path)
    except ValueError as exc:
        return {"status": STATUS_ERROR, "message": str(exc), "data": None}

    project_target = str(issue.get("project") or "").strip()
    project_root, project_name = resolve_target(project_target, base_dir=issue_path.parent)
    project_display = project_name or project_root.name

    memory = load_project_memory(project_root)
    context = load_project_context(project_root)
    plan = detect_plan(project_root / "docs")
    triage = analyze_issue(issue, project_root, context, memory, plan)
    options = build_options(issue, triage, plan)
    memory_follow_up = build_memory_follow_up(project_root, triage)
    plan_source = {
        "plan.json": "docs/plan.json",
        "PLAN.md": "docs/PLAN.md",
        "IMPLEMENTATION_PLAN.md": "docs/IMPLEMENTATION_PLAN.md",
        "none": "none",
    }.get(plan.source, plan.source)
    memory_source = "memory/INDEX.md" if memory.get("path") else "missing"

    status = STATUS_OK
    if triage.get("confidence") == "low" or not context.get("sources"):
        status = STATUS_WARNING
    if not project_root.exists():
        status = STATUS_WARNING

    message = f"FIX triage 已生成：{project_display} | confidence={triage.get('confidence')} | repro={triage.get('reproducibility')}"

    # 环境状态检查
    env_status, env_detail = check_environment_status(project_root)
    
    return {
        "status": status,
        "message": message,
        "data": {
            "project": project_display,
            "project_root": rel_path(project_root, ROOT),
            "issue_source": rel_path(issue_path, ROOT),
            "dry_run": dry_run,
            "context_sources": context.get("sources") or [],
            "memory_source": memory_source,
            "plan_source": plan_source,
            "triage": triage,
            "options": options,
            "memory_follow_up": memory_follow_up,
            "environment": {
                "status": env_status,
                "detail": env_detail
            }
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEV_SDD:FIX 执行辅助 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  读取 issue JSON、项目上下文和项目 memory，先做 triage 再输出双层修复选项。

示例:
  python3 .claude/tools/fix/run.py skill-tests/fixtures/fix/repro-issue.json --json --dry-run
  python3 .claude/tools/fix/run.py skill-tests/fixtures/fix/sparse-issue.json --json
""",
    )
    parser.add_argument("issue", help="issue JSON 路径")
    parser.add_argument("--json", action="store_true", help="输出机器可解析 JSON")
    parser.add_argument("--dry-run", action="store_true", help="只输出 triage/option 结果，不执行写操作")
    args = parser.parse_args()

    result = run(args.issue, args.dry_run)
    out(result, args.json)
    if result.get("status") == STATUS_ERROR:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
