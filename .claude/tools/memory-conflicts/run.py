#!/usr/bin/env python3
from __future__ import annotations

"""Detect and arbitrate conflicting DEV_SDD memory entries."""

import argparse
import hashlib
import importlib.util
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)

ROOT = workflow_cli_common.find_framework_root(__file__)

MEMORY_PATTERNS = ("*.md", "*.yaml", "*.yml")
EXCLUDED_PARTS = {"sessions", "reports", "__pycache__"}
NEGATIVE_TERMS = ("禁止", "不得", "不要", "不能", "never", "must not", "cannot", "can't", "do not")
REQUIRED_TERMS = ("必须", "需要", "应", "always", "must", "should", "require")
CONFIDENCE_SCORE = {"high": 3, "medium": 2, "low": 1, "": 0}


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _rel(path: Path) -> str:
    return workflow_cli_common.rel_path(path, ROOT)


def _iter_memory_files(project_root: Path | None) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = [("framework", ROOT / "memory")]
    if project_root is not None:
        roots.append(("project", project_root / "memory"))
    files: list[tuple[str, Path]] = []
    for scope, root in roots:
        if not root.exists():
            continue
        for pattern in MEMORY_PATTERNS:
            for path in root.rglob(pattern):
                if path.name == "memory_usage.jsonl":
                    continue
                rel_parts = set(path.relative_to(root).parts)
                if EXCLUDED_PARTS & rel_parts:
                    continue
                files.append((scope, path))
    return sorted(files, key=lambda item: str(item[1]))


def _metadata(content: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    lines = content.splitlines()
    in_frontmatter = bool(lines and lines[0].strip() == "---")
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if idx > 0 and in_frontmatter and stripped == "---":
            break
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", stripped)
        if match:
            key, value = match.groups()
            meta[key.lower()] = value.strip().strip("'\"")
        if not in_frontmatter and idx > 30:
            break
    return meta


def _title(path: Path, content: str, meta: dict[str, str]) -> str:
    if meta.get("title"):
        return meta["title"]
    if meta.get("proposed_rule"):
        return meta["proposed_rule"]
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return path.stem


def _entry_id(path: Path, meta: dict[str, str]) -> str:
    for key in ("id", "memory_id", "candidate_id"):
        if meta.get(key):
            return meta[key]
    match = re.search(r"(MEM_[A-Z0-9_]+|[A-Z]+_CAND_[A-Z0-9_-]+)", path.stem)
    if match:
        return match.group(1)
    # INDEX.md and other structural files are unique by path, not by basename.
    return _rel(path)


def _normalized_title(title: str) -> str:
    text = re.sub(r"[`*_#>\[\]():/\\.,，。；;！!?？\-]+", " ", title.lower())
    words = [word for word in text.split() if word not in {"the", "a", "an", "and", "or", "必须", "禁止"}]
    return " ".join(words[:12]).strip()


def _polarity(content: str) -> str:
    lower = content.lower()
    has_negative = any(term in lower for term in NEGATIVE_TERMS)
    has_required = any(term in lower for term in REQUIRED_TERMS)
    if has_negative and not has_required:
        return "prohibit"
    if has_required and not has_negative:
        return "require"
    if has_negative and has_required:
        return "mixed"
    return "neutral"


def _scope_score(scope: str, path: str) -> int:
    if path.startswith("memory/critical/"):
        return 50
    if path.startswith("memory/important/"):
        return 40
    if path.startswith("memory/domains/"):
        return 30
    if scope == "framework":
        return 20
    return 10


def _date_score(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return value


def collect_entries(project: str | None = None) -> dict[str, Any]:
    project_root = None
    project_label = None
    if project:
        project_root, project_label = workflow_cli_common.resolve_target_project(project, ROOT)
    elif workflow_cli_common.detect_active_project(ROOT):
        project_root, project_label = workflow_cli_common.resolve_target_project(None, ROOT)

    entries = []
    for scope, path in _iter_memory_files(project_root if project_root and project_root.exists() else None):
        content = _safe_read(path)
        if not content.strip():
            continue
        meta = _metadata(content)
        rel = _rel(path)
        status = (meta.get("status") or "active").lower()
        confidence = (meta.get("confidence") or "").lower()
        title = _title(path, content, meta)
        digest = hashlib.sha1(re.sub(r"\s+", " ", content).strip().encode("utf-8")).hexdigest()[:12]
        entries.append({
            "id": _entry_id(path, meta),
            "title": title,
            "normalized_title": _normalized_title(title),
            "scope": scope,
            "path": rel,
            "status": status,
            "confidence": confidence,
            "updated": meta.get("updated") or meta.get("last_updated") or meta.get("date") or "",
            "digest": digest,
            "polarity": _polarity(content[:2000]),
        })
    return {"project": project_label, "entries": entries}


def _winner(entries: list[dict[str, Any]]) -> dict[str, Any]:
    def key(entry: dict[str, Any]) -> tuple[int, int, str, int, str]:
        status_score = 0 if entry.get("status") in {"deprecated", "archived", "rejected"} else 1
        confidence = CONFIDENCE_SCORE.get(str(entry.get("confidence") or "").lower(), 0)
        updated = _date_score(str(entry.get("updated") or ""))
        scope = _scope_score(str(entry.get("scope") or ""), str(entry.get("path") or ""))
        return status_score, confidence, updated, scope, str(entry.get("path") or "")

    return sorted(entries, key=key, reverse=True)[0]


def _arbitrate(conflict_type: str, key: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    winner = _winner(entries)
    losers = [entry["path"] for entry in entries if entry["path"] != winner["path"]]
    decision = "keep_winner_review_losers"
    reason = "active/high-confidence/newer/framework memory takes precedence; conflicting entries require human review before deletion"
    if any(entry.get("status") in {"deprecated", "archived", "rejected"} for entry in entries):
        decision = "prefer_active_over_inactive"
        reason = "inactive entries lose unless they contain newer evidence"
    return {"decision": decision, "winner": winner["path"], "losers": losers, "reason": reason}


def find_conflicts(project: str | None = None) -> dict[str, Any]:
    collected = collect_entries(project)
    entries = collected["entries"]
    conflicts = []

    by_id: dict[str, list[dict[str, Any]]] = {}
    by_title: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        by_id.setdefault(entry["id"], []).append(entry)
        if entry["normalized_title"]:
            by_title.setdefault(entry["normalized_title"], []).append(entry)

    seen: set[tuple[str, str]] = set()
    for key, group in by_id.items():
        digests = {item["digest"] for item in group}
        if len(group) > 1 and len(digests) > 1:
            seen.add(("duplicate_id", key))
            conflicts.append({
                "type": "duplicate_id",
                "key": key,
                "entries": group,
                "arbitration": _arbitrate("duplicate_id", key, group),
            })

    for key, group in by_title.items():
        active = [item for item in group if item.get("status") not in {"deprecated", "archived", "rejected"}]
        polarities = {item["polarity"] for item in active if item["polarity"] != "neutral"}
        if len(active) > 1 and {"require", "prohibit"}.issubset(polarities) and ("policy_polarity", key) not in seen:
            conflicts.append({
                "type": "policy_polarity",
                "key": key,
                "entries": active,
                "arbitration": _arbitrate("policy_polarity", key, active),
            })

    return {
        "project": collected["project"],
        "entries_count": len(entries),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV_SDD memory conflict arbitration")
    parser.add_argument("--project", default=None, help="project name/path; defaults to active project")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = find_conflicts(args.project)
    status = "warning" if data["conflict_count"] else "ok"
    payload = {"status": status, "message": f"memory conflicts: {data['conflict_count']}", "data": data}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["message"])
        for conflict in data["conflicts"]:
            print(f"- {conflict['type']} {conflict['key']}: winner={conflict['arbitration']['winner']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
