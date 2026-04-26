#!/usr/bin/env python3
from __future__ import annotations

"""Classify task text for DEV_SDD context-probe and optional memory usage logging."""

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


RULES: list[dict[str, Any]] = [
    {
        "dimension": "网络编程",
        "domain": "network_code",
        "keywords": ["socket", "recv", "send", "TCP", "UDP", "连接", "服务器"],
        "auto_load": ["MEM_F_C_004", "MEM_F_C_005", "MEM_F_I_001", "MEM_F_I_002"],
    },
    {
        "dimension": "异步网络",
        "domain": "network_code",
        "keywords": ["asyncio", "aiohttp", "websocket", "StreamReader", "httpx"],
        "auto_load": ["memory/domains/concurrency/INDEX.md", "MEM_F_C_004"],
    },
    {
        "dimension": "HTTP 协议",
        "domain": "http",
        "keywords": ["HTTP", "响应", "请求", "状态码", "header", "CGI"],
        "auto_load": ["memory/domains/http/INDEX.md"],
    },
    {
        "dimension": "TDD 问题",
        "domain": "tdd_patterns",
        "keywords": ["测试失败", "RED", "断言", "assert", "测试通过不了"],
        "auto_load": ["MEM_F_I_006", "MEM_F_C_003", "memory/domains/tdd_patterns/INDEX.md"],
    },
    {
        "dimension": "类型安全",
        "domain": "type_safety",
        "keywords": ["bytes", "str", "int", "dtype", "类型错误", "TypeError"],
        "auto_load": ["MEM_F_C_002", "memory/domains/type_safety/INDEX.md"],
    },
    {
        "dimension": "多线程",
        "domain": "concurrency",
        "keywords": ["线程", "threading", "并发", "锁", "deadlock"],
        "auto_load": ["MEM_F_I_007", "memory/domains/concurrency/INDEX.md"],
    },
    {
        "dimension": "复杂度评估",
        "domain": "agent_workflow",
        "keywords": ["新项目", "开始开发", "实现", "系统"],
        "auto_load": [".claude/skills/complexity-assess/SKILL.md"],
    },
    {
        "dimension": "记忆沉淀",
        "domain": "agent_workflow",
        "keywords": ["完成了", "交付", "全部通过", "项目结束", "经验沉淀", "memory"],
        "auto_load": [".claude/skills/memory-update/SKILL.md"],
    },
    {
        "dimension": "验证阶段",
        "domain": "agent_workflow",
        "keywords": ["VALIDATE", "验收", "检查实现", "契约", "接口一致性"],
        "auto_load": [".claude/skills/observe-verify/SKILL.md"],
    },
    {
        "dimension": "框架改进",
        "domain": "agent_workflow",
        "keywords": ["candidate", "候选", "skill-review", "规则提升", "框架改进"],
        "auto_load": [".claude/tools/skill-tracker/tracker.py"],
    },
]


def _matches(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def classify(text: str, load_limit: int = 4) -> dict[str, Any]:
    matched_rules = [rule for rule in RULES if _matches(text, rule["keywords"])]
    dimensions = [rule["dimension"] for rule in matched_rules]
    domains = []
    auto_load = []
    skipped = []
    for rule in matched_rules:
        domain = rule.get("domain")
        if domain and domain not in domains:
            domains.append(domain)
        for item in rule["auto_load"]:
            if item in auto_load:
                continue
            if len(auto_load) < load_limit:
                auto_load.append(item)
            else:
                skipped.append(item)
    return {
        "matched_dimensions": dimensions,
        "auto_load": auto_load if auto_load else ["仅 CRITICAL"],
        "skipped": skipped,
        "candidate_domains": domains,
    }


def render_block(result: dict[str, Any]) -> str:
    matched = result["matched_dimensions"] or ["无明确匹配"]
    auto_load = result["auto_load"] or ["仅 CRITICAL"]
    lines = ["[CONTEXT-PROBE]", f"匹配维度: {', '.join(matched)}", f"自动加载: {', '.join(auto_load)}"]
    if result.get("skipped"):
        lines.append(f"跳过加载: {', '.join(result['skipped'])}")
    lines.append("临时规则: 无")
    lines.append("[/CONTEXT-PROBE]")
    return "\n".join(lines)


def _project_root(project_arg: str | None) -> tuple[Path, str]:
    project_root, label = workflow_cli_common.resolve_target_project(project_arg, ROOT)
    if project_root is None or not label:
        raise SystemExit("No active project detected")
    return project_root, label


def record_loaded(project_arg: str | None, task_text: str, loaded: list[str]) -> list[dict[str, Any]]:
    project_root, project = _project_root(project_arg)
    path = project_root / "memory" / "memory_usage.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    events = []
    for memory_id in loaded:
        if memory_id == "仅 CRITICAL":
            continue
        source = "framework"
        if memory_id.startswith("memory/domains/"):
            source = "domain"
        elif memory_id.startswith(".claude/"):
            source = "skill"
        event = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "project": project,
            "memory_id": memory_id,
            "source": source,
            "task": task_text,
            "outcome": "loaded",
            "note": "recorded_by_context_probe",
        }
        events.append(event)
    if events:
        with open(path, "a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV_SDD context-probe classifier")
    parser.add_argument("text", nargs="*", help="task text to classify")
    parser.add_argument("--json", action="store_true", help="emit JSON envelope")
    parser.add_argument("--project", default=None, help="project name/path for --record-loaded")
    parser.add_argument("--record-loaded", action="store_true", help="record auto_load entries to memory_usage.jsonl")
    parser.add_argument("--load-limit", type=int, default=4, help="maximum memory entries to auto-load")
    args = parser.parse_args()

    text = " ".join(args.text).strip()
    result = classify(text, load_limit=max(1, args.load_limit))
    events = []
    if args.record_loaded:
        events = record_loaded(args.project, text, result["auto_load"])
    if args.json:
        print(json.dumps({"status": "ok", "message": "context-probe classified", "data": {**result, "recorded_events": events}}, ensure_ascii=False, indent=2))
    else:
        print(render_block(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
