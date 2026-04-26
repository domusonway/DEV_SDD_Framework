#!/usr/bin/env python3
from __future__ import annotations

"""Record and summarize memory usage/effectiveness events."""

import argparse
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)

ROOT = workflow_cli_common.find_framework_root(__file__)

OUTCOMES = {"loaded", "applied", "helped", "neutral", "misled", "stale"}


def _project_root(project_arg: str | None) -> tuple[Path, str]:
    project_root, label = workflow_cli_common.resolve_target_project(project_arg, ROOT)
    if project_root is None or not label:
        raise SystemExit("No active project detected")
    return project_root, label


def _log_path(project_root: Path) -> Path:
    memory_dir = project_root / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir / "memory_usage.jsonl"


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def cmd_record(args) -> dict[str, Any]:
    if args.outcome not in OUTCOMES:
        raise SystemExit(f"invalid outcome: {args.outcome}")
    project_root, project = _project_root(args.project)
    path = _log_path(project_root)
    event = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "project": project,
        "memory_id": args.memory_id,
        "source": args.source,
        "task": args.task,
        "outcome": args.outcome,
        "note": args.note,
    }
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return {"file": workflow_cli_common.rel_path(path, ROOT), "event": event}


def cmd_summary(args) -> dict[str, Any]:
    project_root, project = _project_root(args.project)
    path = _log_path(project_root)
    events = _read_events(path)
    by_outcome: dict[str, int] = {}
    by_memory: dict[str, dict[str, int]] = {}
    for event in events:
        outcome = str(event.get("outcome") or "unknown")
        memory_id = str(event.get("memory_id") or "unknown")
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        by_memory.setdefault(memory_id, {})[outcome] = by_memory.setdefault(memory_id, {}).get(outcome, 0) + 1
    return {
        "project": project,
        "file": workflow_cli_common.rel_path(path, ROOT),
        "total": len(events),
        "by_outcome": by_outcome,
        "by_memory": by_memory,
    }


def _prune_recommendations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, int]] = {}
    for event in events:
        memory_id = str(event.get("memory_id") or "unknown")
        outcome = str(event.get("outcome") or "unknown")
        counts.setdefault(memory_id, {})[outcome] = counts.setdefault(memory_id, {}).get(outcome, 0) + 1
    recommendations = []
    for memory_id, by_outcome in sorted(counts.items()):
        helped = by_outcome.get("helped", 0)
        harmful = by_outcome.get("misled", 0) + by_outcome.get("stale", 0)
        neutral = by_outcome.get("neutral", 0) + by_outcome.get("loaded", 0)
        if harmful > helped:
            action = "deprecate"
            reason = "misled_or_stale_exceeds_helped"
        elif neutral >= 3 and helped == 0:
            action = "review"
            reason = "frequently_loaded_without_help_signal"
        else:
            action = "keep"
            reason = "no_pruning_signal"
        recommendations.append({
            "memory_id": memory_id,
            "action": action,
            "reason": reason,
            "counts": by_outcome,
        })
    return recommendations


def cmd_prune(args) -> dict[str, Any]:
    project_root, project = _project_root(args.project)
    path = _log_path(project_root)
    events = _read_events(path)
    recommendations = _prune_recommendations(events)
    return {
        "project": project,
        "file": workflow_cli_common.rel_path(path, ROOT),
        "recommendations": recommendations,
        "deprecate_count": sum(1 for item in recommendations if item["action"] == "deprecate"),
        "review_count": sum(1 for item in recommendations if item["action"] == "review"),
    }


def cmd_deprecate(args) -> dict[str, Any]:
    project_root, project = _project_root(args.project)
    deprecated_path = project_root / "memory" / "memory_deprecations.jsonl"
    deprecated_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "project": project,
        "memory_id": args.memory_id,
        "reason": args.reason,
        "replacement": args.replacement,
    }
    with open(deprecated_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"file": workflow_cli_common.rel_path(deprecated_path, ROOT), "record": record}


def emit(payload: dict[str, Any], as_json: bool, message: str) -> None:
    if as_json:
        print(json.dumps({"status": "ok", "message": message, "data": payload}, ensure_ascii=False, indent=2))
        return
    print(message)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV_SDD memory usage/effectiveness tracker")
    subparsers = parser.add_subparsers(dest="cmd")

    record = subparsers.add_parser("record", help="record a memory usage event")
    record.add_argument("memory_id")
    record.add_argument("--project", default=None)
    record.add_argument("--source", default="unknown", help="framework | project | domain | candidate")
    record.add_argument("--task", default="")
    record.add_argument("--outcome", default="loaded", choices=sorted(OUTCOMES))
    record.add_argument("--note", default="")
    record.add_argument("--json", action="store_true")

    summary = subparsers.add_parser("summary", help="summarize memory usage events")
    summary.add_argument("--project", default=None)
    summary.add_argument("--json", action="store_true")

    prune = subparsers.add_parser("prune", help="recommend memory pruning/deprecation actions")
    prune.add_argument("--project", default=None)
    prune.add_argument("--json", action="store_true")

    deprecate = subparsers.add_parser("deprecate", help="record a memory deprecation decision")
    deprecate.add_argument("memory_id")
    deprecate.add_argument("--project", default=None)
    deprecate.add_argument("--reason", required=True)
    deprecate.add_argument("--replacement", default="")
    deprecate.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.cmd == "record":
        emit(cmd_record(args), args.json, "memory usage recorded")
        return 0
    if args.cmd == "summary":
        emit(cmd_summary(args), args.json, "memory usage summary")
        return 0
    if args.cmd == "prune":
        emit(cmd_prune(args), args.json, "memory pruning recommendations")
        return 0
    if args.cmd == "deprecate":
        emit(cmd_deprecate(args), args.json, "memory deprecation recorded")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
