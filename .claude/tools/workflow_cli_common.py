#!/usr/bin/env python3
"""Shared root and target resolution helpers for workflow CLIs."""

from __future__ import annotations

import os
import re
from typing import Any
from pathlib import Path


def is_framework_root(path: Path) -> bool:
    return (path / "AGENTS.md").exists() and (path / "memory" / "INDEX.md").exists()


def _iter_search_roots(anchor: Path) -> list[Path]:
    resolved = anchor.resolve()
    start = resolved if resolved.is_dir() else resolved.parent
    return [start] + list(start.parents)


def find_framework_root(anchor: str | Path | None = None) -> Path:
    search_anchors: list[Path] = []
    if anchor is not None:
        search_anchors.append(Path(anchor))
    search_anchors.append(Path.cwd())

    seen: set[Path] = set()
    for search_anchor in search_anchors:
        for candidate in _iter_search_roots(search_anchor):
            if candidate in seen:
                continue
            seen.add(candidate)
            if is_framework_root(candidate):
                return candidate
    return Path.cwd().resolve()


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def parse_project_from_text(content: str) -> str | None:
    if not content:
        return None
    match = re.search(r"^PROJECT:\s*(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def detect_active_project(root: Path) -> str | None:
    for rel in ["AGENTS.md", "CLAUDE.md"]:
        project = parse_project_from_text(safe_read_text(root / rel))
        if project:
            return project
    return os.environ.get("PROJECT")


def rel_path(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _project_label(path: Path) -> str | None:
    return path.name or None


def resolve_target_project(target_arg: str | None, root: Path, base_dir: Path | None = None) -> tuple[Path | None, str | None]:
    if not target_arg:
        active_project = detect_active_project(root)
        if not active_project:
            return None, None
        target = (root / "projects" / active_project).resolve()
        return target, active_project

    raw = Path(target_arg)
    if raw.is_absolute():
        resolved = raw.resolve()
        return resolved, _project_label(resolved)

    bases: list[Path] = []
    if base_dir is not None:
        bases.append(base_dir.resolve())
    bases.extend([Path.cwd().resolve(), root.resolve()])

    candidates: list[Path] = []
    seen_candidates: set[Path] = set()
    for base in bases:
        candidate = (base / raw).resolve()
        if candidate in seen_candidates:
            continue
        seen_candidates.add(candidate)
        candidates.append(candidate)

    if not (raw.parts and raw.parts[0] == "projects"):
        project_candidate = (root / "projects" / raw).resolve()
        if project_candidate not in seen_candidates:
            candidates.append(project_candidate)

    for candidate in candidates:
        if candidate.exists():
            return candidate, _project_label(candidate)

    fallback = (root / raw).resolve() if raw.parts and raw.parts[0] == "projects" else (root / "projects" / raw).resolve()
    return fallback, Path(target_arg).name


MANAGED_BEGIN = "<!-- DEV_SDD:MANAGED:BEGIN -->"
MANAGED_END = "<!-- DEV_SDD:MANAGED:END -->"
NOTES_BEGIN = "<!-- DEV_SDD:USER_NOTES:BEGIN -->"
NOTES_END = "<!-- DEV_SDD:USER_NOTES:END -->"


def state_to_icon(state: str) -> str:
    if state == "completed":
        return "x"
    if state == "in_progress":
        return ">"
    if state == "skipped":
        return "~"
    return " "


def render_task_line(task_id: str, name: str, state: str) -> str:
    return f"- [{state_to_icon(state)}] {name} <!-- DEV_SDD:TASK:id={task_id};name={name};state={state} -->"


def render_managed_todo(project: str, tasks: list[dict[str, str]]) -> str:
    lines = [
        f"# {project} · 任务跟踪",
        "",
        "> ⚠️ 执行状态以 `docs/plan.json` 为准；此文件仅记录项目级备注、审计和人工跟进。",
        "",
        MANAGED_BEGIN,
    ]
    for task in tasks:
        lines.append(render_task_line(task["id"], task["name"], task["state"]))
    lines.extend([
        MANAGED_END,
        "",
        NOTES_BEGIN,
        "## 用户备注",
        "<!-- 用户可在此区域自由记录；UPDATE_TODO 默认不会覆盖此区 -->",
        NOTES_END,
        "",
    ])
    return "\n".join(lines)


def ensure_plan_stable_ids(plan: dict[str, Any]) -> bool:
    modules = [m for b in plan.get("batches", []) for m in b.get("modules", []) if isinstance(m, dict)]
    used_ids: set[str] = set()
    max_seq = 0

    for module in modules:
        current_id = str(module.get("id") or "").strip()
        if not current_id:
            continue
        if current_id in used_ids:
            continue
        used_ids.add(current_id)
        match = re.fullmatch(r"T-(\d+)", current_id)
        if match:
            max_seq = max(max_seq, int(match.group(1)))

    changed = False
    next_seq = max_seq + 1
    for module in modules:
        current_id = str(module.get("id") or "").strip()
        if current_id:
            continue
        while f"T-{next_seq:03d}" in used_ids:
            next_seq += 1
        assigned = f"T-{next_seq:03d}"
        module["id"] = assigned
        used_ids.add(assigned)
        next_seq += 1
        changed = True
    return changed


def plan_tasks(plan: dict[str, Any]) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    for batch in plan.get("batches", []):
        for module in batch.get("modules", []):
            if not isinstance(module, dict):
                continue
            tasks.append({
                "id": str(module.get("id") or ""),
                "name": str(module.get("name") or ""),
                "state": str(module.get("state") or "pending"),
            })
    return tasks
