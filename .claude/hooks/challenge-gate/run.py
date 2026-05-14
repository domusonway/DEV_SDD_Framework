#!/usr/bin/env python3
from __future__ import annotations

"""Executable trigger classifier for DEV SDD challenge-gate."""

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[2] / "tools"
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)


FORCED_STAGE_REASONS = {
    "planning": "planning_stage",
    "review": "review_stage",
    "delivery": "delivery_stage",
    "session_end": "session_end_stage",
}

CONCLUSION_KEYWORDS = [
    "complete",
    "completed",
    "done",
    "deliver",
    "delivery",
    "ready",
    "final conclusion",
    "完成",
    "交付",
    "交付就绪",
    "最终结论",
    "验收通过",
    "最优",
]

COMPLEX_KEYWORDS = [
    "long task",
    "complex task",
    "h mode",
    "h-mode",
    "planner",
    "implementer",
    "reviewer",
    "cross module",
    "长任务",
    "复杂任务",
    "H模式",
    "H 模式",
    "跨模块",
]

RED_KEYWORDS = ["red > 2", "red>2", "red 超过 2", "red超过2", "stuck-detector"]
RESUME_KEYWORDS = ["resume", "handoff", "in-progress", "续接", "跨 session", "跨session"]


def _contains_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def _normalize_mode(mode: str) -> str:
    return (mode or "").strip().upper()


def _split_evidence(evidence: str) -> list[str]:
    if not evidence.strip():
        return []
    parts = [part.strip() for part in re.split(r"[;\n]+", evidence) if part.strip()]
    return [part for part in parts if part.lower() not in {"n/a", "none", "无"}]


def _challenge_record_path(project: str, session_slug: str) -> str:
    root = workflow_cli_common.find_framework_root(__file__)
    project_root, _label = workflow_cli_common.resolve_target_project(project, root)
    if project_root is None:
        project_root = root / "projects" / project
    return workflow_cli_common.rel_path(project_root / "memory" / "challenges" / f"{session_slug}.md", root)


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    text = " ".join([args.task or "", args.summary or "", args.conclusion or ""]).strip()
    stage = (args.stage or "analysis").strip().lower()
    mode = _normalize_mode(args.mode)
    red_count = max(0, args.red_count)
    module_count = max(0, args.module_count)
    evidence_items = _split_evidence(args.evidence or "")

    reasons: list[str] = []
    risk_flags: list[str] = []

    if mode == "H":
        reasons.append("complex_mode")
    elif mode == "M" and module_count >= 2:
        reasons.append("cross_module_m_mode")

    if stage in FORCED_STAGE_REASONS:
        reasons.append(FORCED_STAGE_REASONS[stage])

    if red_count > 2 or _contains_any(text, RED_KEYWORDS):
        reasons.append("red_over_two")

    if args.resumed or _contains_any(text, RESUME_KEYWORDS):
        reasons.append("cross_session_resume")

    if _contains_any(text, CONCLUSION_KEYWORDS):
        reasons.append("conclusion_keyword")

    if _contains_any(text, COMPLEX_KEYWORDS):
        reasons.append("complex_task_keyword")

    deduped_reasons = []
    for reason in reasons:
        if reason not in deduped_reasons:
            deduped_reasons.append(reason)

    triggered = bool(deduped_reasons)
    if triggered and not evidence_items:
        risk_flags.append("missing_evidence")

    decision = "trigger_challenger" if triggered else "skip"
    record_path = "n/a"
    if triggered and args.project and args.session_slug:
        record_path = _challenge_record_path(args.project, args.session_slug)

    return {
        "triggered": triggered,
        "decision": decision,
        "stage": stage,
        "mode": mode or "unknown",
        "reasons": deduped_reasons,
        "risk_flags": risk_flags,
        "recommended_files": [
            ".claude/hooks/challenge-gate/HOOK.md",
            ".claude/agents/challenger.md",
        ] if triggered else [],
        "evidence_count": len(evidence_items),
        "record_path": record_path,
        "noise_control": {
            "max_questions": 7,
            "max_blocking_questions": 3,
            "requires_evidence_anchor": True,
        },
    }


def render_text(data: dict[str, Any]) -> str:
    triggered = "yes" if data["triggered"] else "no"
    decision = data["decision"]
    reasons = ", ".join(data["reasons"]) if data["reasons"] else "none"
    risk_flags = ", ".join(data["risk_flags"]) if data["risk_flags"] else "none"
    return "\n".join([
        "[CHALLENGE-GATE]",
        f"triggered: {triggered}",
        f"decision: {decision}",
        f"stage: {data['stage']}",
        f"reason: {reasons}",
        f"risk_flags: {risk_flags}",
        f"record: {data['record_path']}",
        "[/CHALLENGE-GATE]",
    ])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DEV SDD challenge-gate trigger classifier")
    parser.add_argument("--task", default="", help="Original task or current task text")
    parser.add_argument("--summary", default="", help="Analysis/process summary")
    parser.add_argument("--conclusion", default="", help="Draft conclusion text")
    parser.add_argument("--stage", default="analysis", help="planning|green|validate|review|delivery|session_end|analysis")
    parser.add_argument("--mode", default="", help="Complexity mode: L|M|H")
    parser.add_argument("--module-count", type=int, default=0, help="Number of affected modules")
    parser.add_argument("--red-count", type=int, default=0, help="Consecutive RED count")
    parser.add_argument("--resumed", action="store_true", help="Whether this run resumes prior in-progress state")
    parser.add_argument("--evidence", default="", help="Semicolon/newline separated evidence summary")
    parser.add_argument("--project", default="", help="Project name for suggested record path")
    parser.add_argument("--session-slug", default="", help="Session slug for suggested record path")
    parser.add_argument("--json", action="store_true", help="Emit JSON envelope")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    data = evaluate(args)
    if args.json:
        message = "challenge-gate triggered" if data["triggered"] else "challenge-gate skipped"
        print(json.dumps({"status": "ok", "message": message, "data": data}, ensure_ascii=False, indent=2))
    else:
        print(render_text(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
