#!/usr/bin/env python3
from __future__ import annotations

"""Classify task text and emit DEV_SDD prompt-policy injections."""

import argparse
import json
from typing import Any


POLICIES: list[dict[str, Any]] = [
    {
        "id": "implementation_fix",
        "priority": 1,
        "keywords": ["实现", "修复", "重构", "fix", "implement", "refactor", "测试通过", "性能达标"],
        "prompt": "质量约束：实现/修复/重构必须遵循 SPEC -> tests -> implementation；优先最小正确改动；测试失败只改实现；完成后运行相关验证，并输出 Sedimentation Decision。",
    },
    {
        "id": "planning_parallel",
        "priority": 2,
        "keywords": ["规划", "计划", "plan.json", "PLAN.md", "多模块", "并行", "依赖", "lane", "冲突"],
        "prompt": "质量约束：规划必须显式列出 deps/blocked_by、parallel group、owner、shared artifacts、writes/reads、handoff artifacts 和 merge gate；必须说明哪些任务可并行、哪些必须串行、哪里可能互相等待或写入冲突。",
    },
    {
        "id": "memory_review",
        "priority": 3,
        "keywords": ["经验沉淀", "memory", "candidate", "人工审核", "promote", "规则提升", "候选"],
        "prompt": "质量约束：经验沉淀和候选审核必须包含 evidence、scope、confidence、risk、status、validated_projects 和 rollback/deprecate 边界；不得把单项目低置信经验直接提升为框架规则。",
    },
    {
        "id": "doc_creation",
        "priority": 4,
        "keywords": ["创建文档", "写文档", "记录", "报告", "方案文档", "文档"],
        "prompt": "质量约束：创建或修改文档前先使用 doc-template 判断文档类型与归属位置，并输出 `[DOC-TEMPLATE]` 块；框架级文档放 root docs/，项目执行文档放 projects/<PROJECT>/docs/，任务细节放 docs/sub_docs/；文档正文默认尽可能使用中文，专业术语/API/代码/命令/路径保留原文；保持既有格式和命名风格；不得把生成视图当作真相源；写完后运行 doc-template validate。",
    },
    {
        "id": "review_evaluate_analyze",
        "priority": 5,
        "keywords": ["审查", "评估", "分析", "确认", "风险", "局限", "全面", "准确", "review", "evaluate", "analyze"],
        "prompt": "质量约束：确认检查内容全面、准确、清晰；每一个指标或判断维度必须定义规范；结论必须区分已验证事实、推断和残余风险；若证据不足，明确说明缺口，不得过度确认。",
    },
]


def classify(text: str, limit: int = 3) -> dict[str, Any]:
    lower = text.lower()
    matched = []
    for policy in POLICIES:
        if any(keyword.lower() in lower for keyword in policy["keywords"]):
            matched.append(policy)
    matched = sorted(matched, key=lambda item: int(item["priority"]))[:limit]
    return {
        "matched": [item["id"] for item in matched],
        "injected": [item["prompt"] for item in matched],
    }


def render_block(result: dict[str, Any]) -> str:
    matched = result["matched"]
    injected = result["injected"]
    if not matched:
        return "[PROMPT-POLICY]\nmatched: none\ninjected: none\n[/PROMPT-POLICY]"
    lines = ["[PROMPT-POLICY]", f"matched: {', '.join(matched)}", "injected:"]
    lines.extend(f"- {prompt}" for prompt in injected)
    lines.append("[/PROMPT-POLICY]")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV_SDD prompt-policy classifier")
    parser.add_argument("text", nargs="*", help="task text to classify")
    parser.add_argument("--json", action="store_true", help="emit JSON envelope")
    parser.add_argument("--limit", type=int, default=3, help="maximum policies to inject")
    args = parser.parse_args()

    text = " ".join(args.text).strip()
    result = classify(text, limit=max(1, args.limit))
    if args.json:
        print(json.dumps({"status": "ok", "message": "prompt-policy classified", "data": result}, ensure_ascii=False, indent=2))
    else:
        print(render_block(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
