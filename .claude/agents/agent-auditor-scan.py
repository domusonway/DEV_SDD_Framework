#!/usr/bin/env python3
"""
agent-auditor-scan.py
分析 Agent 协作链路中的系统性缺陷，生成 AGENT_CAND 候选

对应 agent-auditor.md 的可执行实现（A2修复）

用法:
  python3 .claude/agents/agent-auditor-scan.py <project_name>
  python3 .claude/agents/agent-auditor-scan.py --all
"""
import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def find_framework_root() -> Path:
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return current


ROOT = find_framework_root()
CANDIDATES_DIR = ROOT / "memory" / "candidates"


def _project_slug(project: str) -> str:
    """A1修复：用完整项目名 slug 避免三位缩写碰撞"""
    return re.sub(r"[^a-zA-Z0-9]", "-", project).upper()[:20]


def _next_seq(slug: str, prefix: str = "AGENT") -> int:
    if not CANDIDATES_DIR.exists():
        return 1
    pattern = f"{prefix}_CAND_{slug}_*.yaml"
    existing = list(CANDIDATES_DIR.glob(pattern))
    nums = [int(m.group(1)) for f in existing
            if (m := re.search(r"_(\d+)\.yaml$", f.name))]
    return max(nums) + 1 if nums else 1


def load_sessions(project: str) -> list[tuple[Path, str]]:
    sessions_dir = ROOT / "projects" / project / "memory" / "sessions"
    if not sessions_dir.exists():
        return []
    result = []
    for f in sorted(sessions_dir.glob("*.md")):
        try:
            result.append((f, f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return result


def load_plan(project: str) -> dict:
    plan_path = ROOT / "projects" / project / "docs" / "plan.json"
    if not plan_path.exists():
        return {}
    try:
        return json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_existing_candidate_keys() -> set:
    """返回已有候选的去重键集合"""
    keys = set()
    if not CANDIDATES_DIR.exists():
        return keys
    for f in CANDIDATES_DIR.glob("AGENT_CAND_*.yaml"):
        try:
            content = f.read_text(encoding="utf-8")
            m = re.search(r"observed_pattern_key:\s*(.+)", content)
            if m:
                keys.add(m.group(1).strip())
        except Exception:
            pass
    return keys


def write_candidate(slug: str, project: str, ctype: str,
                    evidence: str, proposed: str, target: str,
                    pattern_key: str, domain: str = "agent_workflow") -> Path:
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    seq = _next_seq(slug, "AGENT")
    filepath = CANDIDATES_DIR / f"AGENT_CAND_{slug}_{seq:03d}.yaml"
    content = f"""id: AGENT_CAND_{slug}_{seq:03d}
candidate_type: agent_constraint
source_observer: agent-auditor
source_project: {project}
observed_evidence: |
  {evidence[:400]}
observed_pattern_key: {pattern_key}
proposed_rule: "{proposed}"
target_file: {target}
proposed_diff: |
  在相关 Agent 的检查清单中追加：
  - [ ] {proposed}
confidence: low
domain: {domain}
validated_projects:
  - {project}
status: pending_review
created: {datetime.now().strftime('%Y-%m-%d')}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


# ── 维度1：Reviewer 报告中的高频缺陷 ────────────────────────────────────────

# 已知缺陷类型 → (target agent, domain, proposed rule)
DEFECT_PATTERNS = {
    "缺少返回类型注解": (
        ".claude/agents/implementer.md",
        "type_safety",
        "GREEN 阶段完整性自查必须包含：所有公开函数有完整返回类型注解",
    ),
    "return type": (
        ".claude/agents/implementer.md",
        "type_safety",
        "GREEN 阶段完整性自查必须包含：所有公开函数有完整返回类型注解",
    ),
    "测试数量不足": (
        ".claude/agents/implementer.md",
        "tdd_patterns",
        "RED 阶段：测试函数数量必须 ≥ SPEC 行为规格小节数",
    ),
    "PLAN.md 未同步": (
        ".claude/agents/implementer.md",
        "agent_workflow",
        "UPDATE-PLAN 阶段：必须确认 PLAN.md 中本模块已勾选后才能进入下一模块",
    ),
    "接口与 SPEC 不一致": (
        ".claude/agents/implementer.md",
        "type_safety",
        "VALIDATE 阶段必须调用 check_contract.py 验证接口与 SPEC 一致",
    ),
    "复审报告格式不完整": (
        ".claude/agents/reviewer.md",
        "agent_workflow",
        "复审报告必须包含 Hook 观察结果和 test-sync 结果两个章节",
    ),
}


def scan_reviewer_defects(sessions: list) -> list[dict]:
    """扫描 Reviewer 报告中的高频缺陷"""
    findings = []
    for session_path, content in sessions:
        # 提取复审报告块
        for block in re.finditer(
            r"## 待修复项(.*?)(?=\n##|\Z)", content, re.DOTALL
        ):
            block_text = block.group(1)
            for pattern, (target, domain, rule) in DEFECT_PATTERNS.items():
                if pattern.lower() in block_text.lower():
                    findings.append({
                        "pattern": pattern,
                        "target": target,
                        "domain": domain,
                        "rule": rule,
                        "session": session_path.name,
                        "snippet": block_text[:200].replace("\n", " "),
                    })
    return findings


# ── 维度2：PLAN.md 中 [~] 跳过模式 ─────────────────────────────────────────

TECH_KEYWORDS = {
    "async": "concurrency",
    "asyncio": "concurrency",
    "database": "persistence",
    "db": "persistence",
    "redis": "persistence",
    "cache": "persistence",
    "auth": "security",
    "oauth": "security",
    "websocket": "network_code",
    "grpc": "network_code",
}


def scan_skipped_modules(plan: dict) -> list[dict]:
    """分析跳过模块的共同技术特征"""
    skipped = [
        m for b in plan.get("batches", [])
        for m in b.get("modules", [])
        if m.get("state") == "skipped"
    ]
    if len(skipped) < 2:
        return []

    # 检测共同关键词
    findings = []
    tech_counts: dict[str, list] = defaultdict(list)
    for m in skipped:
        name_lower = m["name"].lower()
        risk_lower = m.get("risk", "").lower()
        combined = name_lower + " " + risk_lower
        for kw, domain in TECH_KEYWORDS.items():
            if kw in combined:
                tech_counts[domain].append(m["name"])

    for domain, modules in tech_counts.items():
        if len(modules) >= 2:
            findings.append({
                "domain": domain,
                "modules": modules,
                "rule": f"Planner 风险评估应包含 {domain} 领域的特定风险维度",
                "target": ".claude/agents/planner.md",
            })
    return findings


# ── 维度3：Session 中断模式 ──────────────────────────────────────────────────

INTERRUPT_PATTERNS = {
    "等待依赖接口": (
        "agent_workflow",
        "批次划分前应确认所有依赖接口已标记为 🟢 稳定",
        ".claude/agents/planner.md",
    ),
    "批次粒度": (
        "agent_workflow",
        "批次粒度过大时应拆分为更小批次，每批次不超过 3 个模块",
        ".claude/agents/planner.md",
    ),
    "context.*满|context.*rot|上下文.*退化": (
        "context_budget",
        "H 模式每完成一个批次应执行 context-budget 检查",
        ".claude/agents/implementer.md",
    ),
}


def scan_interrupt_patterns(sessions: list) -> list[dict]:
    """扫描 session 中断原因的系统性模式"""
    findings = []
    for session_path, content in sessions:
        for block in re.finditer(
            r"\[SESSION-END\](.*?)\[/SESSION-END\]", content, re.DOTALL
        ):
            interrupted = block.group(1)
            for pattern, (domain, rule, target) in INTERRUPT_PATTERNS.items():
                if re.search(pattern, interrupted, re.IGNORECASE):
                    findings.append({
                        "domain": domain,
                        "rule": rule,
                        "target": target,
                        "session": session_path.name,
                        "snippet": interrupted[:150].replace("\n", " "),
                    })
    return findings


# ── 主流程 ───────────────────────────────────────────────────────────────────

def scan_project(project: str) -> list[Path]:
    print(f"\n[agent-auditor-scan] 扫描项目: {project}")
    sessions = load_sessions(project)
    plan = load_plan(project)

    if not sessions and not plan:
        print("  ⚠️  无 session 或 plan.json，跳过")
        return []

    slug = _project_slug(project)
    existing_keys = load_existing_candidate_keys()
    new_files = []

    # 维度1：Reviewer 缺陷
    defect_counts: dict[str, int] = defaultdict(int)
    defect_meta: dict[str, dict] = {}
    for f in scan_reviewer_defects(sessions):
        key = f"reviewer_defect:{f['pattern']}:{f['target']}"
        defect_counts[key] += 1
        defect_meta[key] = f

    for key, count in defect_counts.items():
        if count >= 1 and key not in existing_keys:
            meta = defect_meta[key]
            fp = write_candidate(
                slug=slug, project=project,
                ctype="agent_constraint",
                evidence=f"Reviewer 报告中发现 '{meta['pattern']}' 缺陷\n"
                         f"session: {meta['session']}\n片段: {meta['snippet']}",
                proposed=meta["rule"],
                target=meta["target"],
                pattern_key=key,
                domain=meta["domain"],
            )
            new_files.append(fp)

    # 维度2：跳过模块
    for f in scan_skipped_modules(plan):
        key = f"skipped_domain:{f['domain']}"
        if key not in existing_keys:
            fp = write_candidate(
                slug=slug, project=project,
                ctype="planner_risk_dimension_missing",
                evidence=f"跳过模块均涉及 {f['domain']} 领域: {', '.join(f['modules'])}",
                proposed=f["rule"],
                target=f["target"],
                pattern_key=key,
                domain=f["domain"],
            )
            new_files.append(fp)

    # 维度3：中断模式
    interrupt_counts: dict[str, int] = defaultdict(int)
    interrupt_meta: dict[str, dict] = {}
    for f in scan_interrupt_patterns(sessions):
        key = f"interrupt:{f['domain']}:{f['target']}"
        interrupt_counts[key] += 1
        interrupt_meta[key] = f

    for key, count in interrupt_counts.items():
        if count >= 2 and key not in existing_keys:  # 中断模式需出现2次才生成候选
            meta = interrupt_meta[key]
            fp = write_candidate(
                slug=slug, project=project,
                ctype="agent_constraint",
                evidence=f"session 中断原因重复出现（{count}次）\n"
                         f"最近: {meta['session']}\n片段: {meta['snippet']}",
                proposed=meta["rule"],
                target=meta["target"],
                pattern_key=key,
                domain=meta["domain"],
            )
            new_files.append(fp)

    if new_files:
        print(f"  ✅ 新增 AGENT_CAND {len(new_files)} 条：")
        for fp in new_files:
            data_m = re.search(r'proposed_rule: "(.+)"',
                               fp.read_text(encoding="utf-8"))
            rule = data_m.group(1)[:55] if data_m else fp.stem
            print(f"     {fp.name}  →  {rule}")
    else:
        print("  ✅ 无新 Agent 协作缺口候选")

    return new_files


def main():
    parser = argparse.ArgumentParser(description="Agent-Auditor — 分析 Agent 协作缺口")
    parser.add_argument("project", nargs="?", help="项目名称")
    parser.add_argument("--all", action="store_true", help="扫描所有项目")
    args = parser.parse_args()

    projects = []
    if args.all:
        projects_dir = ROOT / "projects"
        projects = [
            d.name for d in projects_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]
    elif args.project:
        projects = [args.project]
    else:
        claude_md = ROOT / "CLAUDE.md"
        if claude_md.exists():
            m = re.search(r"^PROJECT:\s*(.+)$",
                          claude_md.read_text(encoding="utf-8"), re.MULTILINE)
            if m:
                projects = [m.group(1).strip()]

    if not projects:
        print("❌ 未指定项目，请提供项目名或使用 --all")
        sys.exit(1)

    total = 0
    for p in projects:
        total += len(scan_project(p))

    print(f"\n[agent-auditor-scan] 完成，共生成 {total} 条候选")
    if total > 0:
        print("  查看候选：python3 .claude/tools/skill-tracker/tracker.py candidates")


if __name__ == "__main__":
    main()
