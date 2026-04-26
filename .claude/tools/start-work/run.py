#!/usr/bin/env python3
"""
start-work/run.py

用途:
  /DEV_SDD:start-work 的执行辅助 CLI。
  统一探测项目上下文、Session 续接状态、计划进度和下一步动作。

用法:
  python3 .claude/tools/start-work/run.py [project-name] [--json]

示例:
  python3 .claude/tools/start-work/run.py
  python3 .claude/tools/start-work/run.py structured-light-stereo
  python3 .claude/tools/start-work/run.py --json
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

PROMPT_POLICY_SPEC = importlib.util.spec_from_file_location("prompt_policy", TOOLS_ROOT / "prompt-policy" / "run.py")
assert PROMPT_POLICY_SPEC and PROMPT_POLICY_SPEC.loader
prompt_policy = importlib.util.module_from_spec(PROMPT_POLICY_SPEC)
PROMPT_POLICY_SPEC.loader.exec_module(prompt_policy)

CONTEXT_PROBE_SPEC = importlib.util.spec_from_file_location("context_probe", TOOLS_ROOT / "context-probe" / "run.py")
assert CONTEXT_PROBE_SPEC and CONTEXT_PROBE_SPEC.loader
context_probe = importlib.util.module_from_spec(CONTEXT_PROBE_SPEC)
CONTEXT_PROBE_SPEC.loader.exec_module(context_probe)

MEMORY_SEARCH_SPEC = importlib.util.spec_from_file_location("memory_search", TOOLS_ROOT / "memory-search" / "run.py")
assert MEMORY_SEARCH_SPEC and MEMORY_SEARCH_SPEC.loader
memory_search = importlib.util.module_from_spec(MEMORY_SEARCH_SPEC)
MEMORY_SEARCH_SPEC.loader.exec_module(memory_search)

DOC_TEMPLATE_SPEC = importlib.util.spec_from_file_location("doc_template", TOOLS_ROOT / "doc-template" / "run.py")
assert DOC_TEMPLATE_SPEC and DOC_TEMPLATE_SPEC.loader
doc_template = importlib.util.module_from_spec(DOC_TEMPLATE_SPEC)
DOC_TEMPLATE_SPEC.loader.exec_module(doc_template)


STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"

MANAGED_BEGIN = "<!-- DEV_SDD:MANAGED:BEGIN -->"
MANAGED_END = "<!-- DEV_SDD:MANAGED:END -->"

TASK_LINE_RE = re.compile(
    r"^\s*-\s*\[([ xX>~])\]\s*(.*?)\s*<!--\s*DEV_SDD:TASK:id=([^;]+);name=([^;]+);state=([a-z_]+)\s*-->\s*$"
)


def out(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    status_val = str(payload.get("status") or "")
    icon = {STATUS_OK: "✅", STATUS_WARNING: "⚠️", STATUS_ERROR: "❌"}.get(status_val, "ℹ️")
    print(f"{icon}  {payload.get('message', '')}")
    data = payload.get("data") or {}
    print("[START-WORK]")
    print(f"项目: {data.get('project', 'unknown')}")
    print(f"Session: {data.get('session', {}).get('state', 'unknown')}")
    print(f"模式: {data.get('mode', {}).get('detected', 'unknown')}")
    print(f"计划: {data.get('plan', {}).get('summary', '无可用计划信息')}")
    # 环境状态
    env_info = data.get('environment', {})
    if env_info:
        env_status = env_info.get('status', 'unknown')
        env_icon = {"not_found": "📁", "exists_not_activated": "🔧", "activated": "🟢"}.get(env_status, "❓")
        print(f"环境: {env_icon} {env_info.get('detail', '')}")
    prompt_info = data.get("prompt_policy") or {}
    if prompt_info.get("matched"):
        print(f"提示词策略: {', '.join(prompt_info.get('matched', []))}")
    context_info = data.get("context_probe") or {}
    if context_info.get("matched_dimensions"):
        print(f"上下文探测: {', '.join(context_info.get('matched_dimensions', []))}")
    memory_info = data.get("memory_search") or {}
    if memory_info.get("hits"):
        print(f"记忆命中: {len(memory_info.get('hits', []))} 条")
    doc_info = data.get("doc_template") or {}
    if doc_info.get("matched"):
        print(f"文档模板: {doc_info.get('template_id')} -> {doc_info.get('suggested_path')}")
        print(f"文档语言: 默认中文，专业术语/API/代码/命令/路径保留原文 ({doc_info.get('language_policy')})")
    print(f"下一步: {data.get('next_action', '请先补齐项目上下文')}")
    print("[/START-WORK]")


def find_framework_root() -> Path:
    return workflow_cli_common.find_framework_root(__file__)


ROOT = find_framework_root()


def safe_read_text(path: Path) -> str:
    return workflow_cli_common.safe_read_text(path)


def parse_project_from_text(content: str) -> str | None:
    if not content:
        return None
    m = re.search(r"^PROJECT:\s*(.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def detect_active_project(root: Path) -> str | None:
    return workflow_cli_common.detect_active_project(root)


def rel_path(path: Path, base: Path) -> str:
    return workflow_cli_common.rel_path(path, base)


def detect_mode(project_claude: Path) -> dict[str, str]:
    content = safe_read_text(project_claude)
    if not content:
        return {"detected": "unknown", "source": "missing"}

    m = re.search(r"工作模式:\s*([LMH])", content)
    if m:
        return {"detected": m.group(1), "source": "projects/<PROJECT>/CLAUDE.md"}

    m2 = re.search(r"工作模式:\s*([^\n|]+)", content)
    if m2:
        raw = m2.group(1).strip()
        maybe = raw[0].upper() if raw else "unknown"
        return {"detected": maybe if maybe in {"L", "M", "H"} else raw, "source": "projects/<PROJECT>/CLAUDE.md"}
    return {"detected": "unknown", "source": "unparsed"}


@dataclass
class PlanResult:
    source: str
    summary: str
    next_action: str
    progress: dict[str, Any]
    nodes: list[dict[str, str]]
    parallel: dict[str, Any]


def _module_key(module: dict[str, Any]) -> str:
    return str(module.get("name") or module.get("id") or "").strip()


def _completed_keys(modules: list[dict[str, Any]]) -> set[str]:
    completed: set[str] = set()
    for module in modules:
        if module.get("state") == "completed":
            key = _module_key(module)
            if key:
                completed.add(key)
            module_id = str(module.get("id") or "").strip()
            if module_id:
                completed.add(module_id)
    return completed


def _deps_ready(module: dict[str, Any], completed: set[str]) -> bool:
    deps = module.get("deps") or module.get("blocked_by") or []
    return all(str(dep) in completed for dep in deps)


def _task_summary(module: dict[str, Any]) -> dict[str, Any]:
    execution = module.get("execution") or {}
    return {
        "id": str(module.get("id") or ""),
        "name": str(module.get("name") or ""),
        "state": str(module.get("state") or "pending"),
        "group": str(execution.get("group") or module.get("group") or ""),
        "relation_type": str(module.get("relation_type") or ""),
        "deps": list(module.get("deps") or module.get("blocked_by") or []),
        "parallel_with": list(module.get("parallel_with") or execution.get("parallel_with") or []),
        "handoff_artifacts": list(execution.get("handoff_artifacts") or module.get("handoff_artifacts") or []),
    }


def _ready_tasks_from_modules(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    completed = _completed_keys(modules)
    ready: list[dict[str, Any]] = []
    for module in modules:
        if module.get("state", "pending") not in {"pending", "in_progress"}:
            continue
        if _deps_ready(module, completed):
            ready.append(_task_summary(module))
    return ready


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
            progress={"completed": 0, "total": 0, "percent": 0},
            nodes=[],
            parallel={"ready_tasks": [], "ready_count": 0, "recommended": None},
        )

    all_modules = [m for b in plan.get("batches", []) for m in b.get("modules", [])]
    total = len(all_modules)
    completed = sum(1 for m in all_modules if m.get("state") == "completed")
    in_progress = sum(1 for m in all_modules if m.get("state") == "in_progress")
    pending = sum(1 for m in all_modules if m.get("state", "pending") == "pending")
    percent = round(completed / total * 100) if total else 0
    next_action = _compute_next_action_from_batches(plan)
    nodes: list[dict[str, str]] = []
    for module in all_modules:
        module_id = str(module.get("id") or "").strip()
        if not module_id:
            continue
        nodes.append({
            "id": module_id,
            "name": str(module.get("name") or ""),
            "state": str(module.get("state") or "pending"),
        })
    ready_tasks = _ready_tasks_from_modules(all_modules)
    return PlanResult(
        source="plan.json",
        summary=f"{completed}/{total} 完成（{percent}%）",
        next_action=next_action,
        progress={
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "total": total,
            "percent": percent,
        },
        nodes=nodes,
        parallel={
            "ready_tasks": ready_tasks,
            "ready_count": len(ready_tasks),
            "recommended": ready_tasks[0] if ready_tasks else None,
        },
    )


def _extract_task_name(line: str) -> str:
    text = re.sub(r"^-\s*\[[ xX~>]\]\s*", "", line).strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text.strip() or "未命名任务"


def _load_plan_markdown(path: Path) -> PlanResult | None:
    if not path.exists():
        return None
    content = safe_read_text(path)
    if not content:
        return PlanResult(
            source=path.name,
            summary=f"{path.name} 存在但无法读取",
            next_action=f"检查 {path.name} 文件权限或编码",
            progress={"completed": 0, "pending": 0, "in_progress": 0, "total": 0, "percent": 0},
            nodes=[],
            parallel={"ready_tasks": [], "ready_count": 0, "recommended": None},
        )

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
        parallel={"ready_tasks": [], "ready_count": 0, "recommended": None},
    )


def detect_plan(project_docs: Path) -> PlanResult:
    prioritized: list[tuple[str, Path]] = [
        ("plan.json", project_docs / "plan.json"),
        ("PLAN.md", project_docs / "PLAN.md"),
        ("IMPLEMENTATION_PLAN.md", project_docs / "IMPLEMENTATION_PLAN.md"),
    ]

    json_result = _load_plan_json(prioritized[0][1])
    if json_result is not None:
        return json_result

    for _, path in prioritized[1:]:
        md_result = _load_plan_markdown(path)
        if md_result is not None:
            return md_result

    return PlanResult(
        source="none",
        summary="未检测到 plan.json / PLAN.md / IMPLEMENTATION_PLAN.md",
        next_action="先补齐 BRIEF.md 或 CONTEXT.md + SPEC.md + 计划文件",
        progress={"completed": 0, "in_progress": 0, "pending": 0, "total": 0, "percent": 0},
        nodes=[],
        parallel={"ready_tasks": [], "ready_count": 0, "recommended": None},
    )


def _sort_warnings(warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(warnings, key=lambda item: (
        str(item.get("reason") or ""),
        str(item.get("id") or ""),
        int(item.get("line") or 0),
        str(item.get("detail") or ""),
    ))


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


def reconcile_todo(project_root: Path, plan: PlanResult) -> dict[str, Any]:
    return {
        "status": "not_applicable",
        "matched_ids": [],
        "orphan_ids": [],
        "conflict_ids": [],
        "missing_ids": [],
        "warnings": [{"reason": "docs_todo_deprecated", "detail": "docs/TODO.md 已废弃，启动阶段不再执行 TODO↔plan 对账"}],
    }


def parse_handoff(handoff_path: Path) -> dict[str, Any] | None:
    if not handoff_path.exists():
        return None
    try:
        return json.loads(handoff_path.read_text(encoding="utf-8"))
    except Exception:
        return {"_invalid": True}


def parse_latest_session(session_dir: Path) -> dict[str, Any] | None:
    if not session_dir.exists():
        return None
    files = sorted(session_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    latest = files[0]
    content = safe_read_text(latest)
    if not content:
        return {"file": str(latest), "status": "unknown", "task": "未知"}

    status = "in-progress" if "status: in-progress" in content else ("completed" if "status: completed" in content else "unknown")
    task_m = re.search(r"^task:\s*(.+)$", content, re.MULTILINE)
    next_m = re.search(r"^下次继续:\s*(.+)$", content, re.MULTILINE)
    return {
        "file": rel_path(latest, ROOT),
        "status": status,
        "task": task_m.group(1).strip() if task_m else "未记录",
        "next_step": next_m.group(1).strip() if next_m else "",
    }


def detect_session(project_root: Path, plan_next: str, plan_source: str, plan_progress: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    handoff_path = project_root / "HANDOFF.json"
    handoff = parse_handoff(handoff_path)
    latest_session = parse_latest_session(project_root / "memory" / "sessions")

    if handoff is not None:
        if handoff.get("_invalid"):
            return ({
                "state": "RESUME",
                "handoff_exists": True,
                "handoff_valid": False,
                "latest_session": latest_session,
            }, "HANDOFF.json 存在但格式异常，先修复 HANDOFF.json 再继续", "HANDOFF.json")
        handoff_next = handoff.get("next_action")
        return ({
            "state": "RESUME",
            "handoff_exists": True,
            "handoff_valid": True,
            "handoff": {
                "timestamp": handoff.get("timestamp"),
                "last_completed_module": handoff.get("last_completed_module"),
                "current_state": handoff.get("current_state"),
                "next_action": handoff.get("next_action"),
            },
            "latest_session": latest_session,
        }, handoff_next or plan_next, "HANDOFF.json" if handoff_next else plan_source)

    plan_is_complete = bool(plan_progress.get("total")) and plan_progress.get("completed") == plan_progress.get("total")
    if latest_session and latest_session.get("status") == "in-progress" and plan_is_complete:
        return ({
            "state": "NEW SESSION",
            "handoff_exists": False,
            "latest_session": latest_session,
            "stale_session_ignored": True,
            "stale_reason": "plan_complete",
        }, plan_next, plan_source)

    if latest_session and latest_session.get("status") == "in-progress":
        return ({
            "state": "RESUME",
            "handoff_exists": False,
            "latest_session": latest_session,
        }, latest_session.get("next_step") or f"续接会话任务：{latest_session.get('task', '未记录任务')}", "session")

    return ({
        "state": "NEW SESSION",
        "handoff_exists": False,
        "latest_session": latest_session,
    }, plan_next, plan_source)


def build_context_files(root: Path, project_root: Path | None, project: str) -> dict[str, list[str]]:
    framework_files = [
        "memory/INDEX.md",
        "AGENTS.md",
    ]
    project_files: list[str] = []
    if project_root is not None:
        for path in [project_root / "CLAUDE.md", project_root / "memory" / "INDEX.md"]:
            if path.exists():
                project_files.append(rel_path(path, root))
    return {
        "framework": [p for p in framework_files if (root / p).exists()],
        "project": project_files,
    }


def infer_module_from_task(task_text: str, project_root: Path | None = None) -> str | None:
    if not task_text:
        return None
    patterns = [
        r"([A-Za-z0-9_./-]+)\s*模块",
        r"module\s+([A-Za-z0-9_./-]+)",
        r"--module\s+([A-Za-z0-9_./-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, task_text, re.IGNORECASE)
        if match:
            value = match.group(1).strip("`'\" ，,。")
            if value and value not in {"单", "一个", "某个"}:
                return value
    if project_root is not None:
        modules_root = project_root / "modules"
        if modules_root.exists():
            lower = task_text.lower()
            for path in sorted(modules_root.glob("**/__init__.py")):
                module_name = path.parent.name
                if module_name.lower() in lower:
                    return module_name
    return None


def build_doc_template_signal(task_text: str, project: str | None, project_root: Path | None, prompt_policy_result: dict[str, Any]) -> dict[str, Any]:
    if not task_text or "doc_creation" not in (prompt_policy_result.get("matched") or []):
        return {"matched": False}
    classified = doc_template.classify_text(task_text)
    template_id = classified.get("template_id")
    module = infer_module_from_task(task_text, project_root)
    topic = module or doc_template.slugify(task_text[:40])
    suggested_path = ""
    language_policy = "zh_cn_default_preserve_terms"
    try:
        templates = doc_template.load_templates()
        if template_id in templates:
            language_policy = str(templates[template_id].get("meta", {}).get("language_policy") or language_policy)
            suggested_path, _ = doc_template.render_template(templates[template_id], project, module, topic, None)
    except Exception as exc:
        return {
            "matched": True,
            "template_id": template_id,
            "confidence": classified.get("confidence"),
            "suggested_path": "",
            "language_policy": language_policy,
            "validation_required": True,
            "error": str(exc),
            "doc_template_block": "",
        }
    block = (
        "[DOC-TEMPLATE]\n"
        f"intent: {template_id}\n"
        f"template_id: {template_id}\n"
        f"confidence: {classified.get('confidence')}\n"
        f"target_path: {suggested_path}\n"
        "language: zh-CN default, preserve technical terms\n"
        "validation_required: true\n"
        "[/DOC-TEMPLATE]"
    )
    return {
        "matched": True,
        "template_id": template_id,
        "confidence": classified.get("confidence"),
        "matched_keywords": classified.get("matched_keywords", []),
        "suggested_path": suggested_path,
        "language_policy": language_policy,
        "module": module,
        "validation_required": True,
        "validate_command": f"python3 .claude/tools/doc-template/run.py validate {suggested_path} --template {template_id} --json" if suggested_path else "",
        "doc_template_block": block,
    }


def run(project_arg: str | None, task_text: str = "") -> dict[str, Any]:
    active_project = detect_active_project(ROOT)
    project_root, target_label = workflow_cli_common.resolve_target_project(project_arg, ROOT)
    project = target_label or project_arg or active_project
    prompt_policy_result = prompt_policy.classify(task_text or "") if task_text else {"matched": [], "injected": []}
    context_probe_result = context_probe.classify(task_text or "") if task_text else {"matched_dimensions": [], "auto_load": ["仅 CRITICAL"], "skipped": [], "candidate_domains": []}
    memory_search_result = memory_search.search(task_text or "", project=project_arg if project_arg else None, top_k=5) if task_text else {"query": "", "tokens": [], "project": project, "hits": []}
    doc_template_result = build_doc_template_signal(task_text or "", project, project_root, prompt_policy_result)
    if not project:
        return {
            "status": STATUS_WARNING,
            "message": "未检测到激活项目，无法执行 start-work 上下文装配",
            "data": {
                "project": None,
                "context_files": {"framework": ["memory/INDEX.md", "AGENTS.md"], "project": []},
                "prompt_policy": prompt_policy_result,
                "context_probe": context_probe_result,
                "memory_search": memory_search_result,
                "doc_template": doc_template_result,
                "session": {"state": "NEW SESSION", "handoff_exists": False, "latest_session": None},
                "mode": {"detected": "unknown", "source": "missing_project"},
                "plan": {
                    "source": "none",
                    "summary": "无项目，未加载计划",
                    "progress": {"completed": 0, "in_progress": 0, "pending": 0, "total": 0, "percent": 0},
                    "next_action": "先执行 /project:new <name> 或 /project:switch <name>",
                },
                "next_action": "先执行 /project:new <name> 或 /project:switch <name>",
            },
        }

    context_files = build_context_files(ROOT, project_root, project)

    if project_root is None or not project_root.exists():
        next_action = f"项目 {project} 不存在；先执行 /project:new {project} 或 /project:switch <existing-project>"
        return {
            "status": STATUS_WARNING,
            "message": f"项目不存在：{project}",
            "data": {
                "project": project,
                "project_path": rel_path(project_root or (ROOT / "projects" / project), ROOT),
                "active_project": active_project,
                "context_files": context_files,
                "prompt_policy": prompt_policy_result,
                "context_probe": context_probe_result,
                "memory_search": memory_search_result,
                "doc_template": doc_template_result,
                "session": {"state": "NEW SESSION", "handoff_exists": False, "latest_session": None},
                "mode": {"detected": "unknown", "source": "missing_project_dir"},
                "plan": {
                    "source": "none",
                    "summary": "项目目录不存在，无法读取计划",
                    "progress": {"completed": 0, "in_progress": 0, "pending": 0, "total": 0, "percent": 0},
                    "next_action": next_action,
                },
                "next_action": next_action,
            },
        }

    mode = detect_mode(project_root / "CLAUDE.md")
    plan = detect_plan(project_root / "docs")
    reconciliation = reconcile_todo(project_root, plan)
    session, next_action, next_action_source = detect_session(project_root, plan.next_action, plan.source, plan.progress)

    status = STATUS_OK
    if mode.get("detected") == "unknown" or plan.source == "none":
        status = STATUS_WARNING

    # 环境状态检查
    env_status, env_detail = check_environment_status(project_root)
    
    return {
        "status": status,
        "message": f"start-work 检查完成：{project} | Session={session['state']} | Plan={plan.summary}",
            "data": {
                "project": project,
                "project_path": rel_path(project_root, ROOT),
                "active_project": active_project,
                "context_files": context_files,
                "prompt_policy": prompt_policy_result,
                "context_probe": context_probe_result,
                "memory_search": memory_search_result,
                "doc_template": doc_template_result,
                "session": session,
            "mode": mode,
            "plan": {
                "source": plan.source,
                "summary": plan.summary,
                "progress": plan.progress,
                "next_action": plan.next_action,
            },
            "parallel": plan.parallel,
            "reconciliation": reconciliation,
            "next_action": next_action,
            "next_action_source": next_action_source,
            "environment": {
                "status": env_status,
                "detail": env_detail
            }
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEV_SDD:start-work 执行辅助 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  生成 /DEV_SDD:start-work 所需的结构化上下文摘要。

示例:
  python3 .claude/tools/start-work/run.py
  python3 .claude/tools/start-work/run.py structured-light-stereo
  python3 .claude/tools/start-work/run.py --json
""",
    )
    parser.add_argument("project", nargs="?", help="可选：显式覆盖目标项目名或项目路径")
    parser.add_argument("--json", action="store_true", help="输出机器可解析 JSON")
    parser.add_argument("--task", default="", help="可选：当前用户任务描述，用于 prompt-policy 分类")
    args = parser.parse_args()

    result = run(args.project, task_text=args.task)
    out(result, args.json)

    if result.get("status") == STATUS_ERROR:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
