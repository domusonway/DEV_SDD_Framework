#!/usr/bin/env python3
"""
skill-tracker/tracker.py
全类型框架改进候选的跨项目追踪与提升工具

用途:
  管理 Meta-Skill Loop 生成的候选规则，支持审核、提升、和候选临时激活（auto_attach）。
  attach/detach 子命令配合 context-probe 的临时规则注入机制，消除候选到实用的等待期。

用法:
  python3 .claude/tools/skill-tracker/tracker.py candidates            # 查看全部候选
  python3 .claude/tools/skill-tracker/tracker.py candidates --type hook_trigger
  python3 .claude/tools/skill-tracker/tracker.py candidates --min-validated 2
  python3 .claude/tools/skill-tracker/tracker.py candidates --auto-attach   # 只看已附加候选
  python3 .claude/tools/skill-tracker/tracker.py candidates --domain network_code
  python3 .claude/tools/skill-tracker/tracker.py attach <id>           # 标记为临时激活
  python3 .claude/tools/skill-tracker/tracker.py detach <id>           # 取消临时激活
  python3 .claude/tools/skill-tracker/tracker.py validate <id> --project <p>
  python3 .claude/tools/skill-tracker/tracker.py approve <id>
  python3 .claude/tools/skill-tracker/tracker.py reject <id> --reason "..."
  python3 .claude/tools/skill-tracker/tracker.py promote <id>
  python3 .claude/tools/skill-tracker/tracker.py status

示例:
  # 查看可临时激活的候选（medium+ confidence）
  python3 .claude/tools/skill-tracker/tracker.py candidates --min-validated 2

  # 标记为临时激活（context-probe 会自动注入其 proposed_diff）
  python3 .claude/tools/skill-tracker/tracker.py attach HOOK_CAND_SDD-TINYHTTPD_001

  # 查看当前已激活的候选（供 context-probe 调用）
  python3 .claude/tools/skill-tracker/tracker.py candidates --auto-attach --status pending_review

  # 取消临时激活
  python3 .claude/tools/skill-tracker/tracker.py detach HOOK_CAND_SDD-TINYHTTPD_001
"""
import sys
import re
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def find_framework_root() -> Path:
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return current


ROOT = find_framework_root()
CANDIDATES_DIR = ROOT / "memory" / "candidates"
CHANGELOG = ROOT / "memory" / "skill-changelog.md"

PROMOTE_TARGETS = {
    "skill_rule": "direct_append",
    "hook_trigger": "direct_append",
    "hook_check": "direct_append",
    "agent_constraint": "direct_append",
    "agent_role_gap": "create_new",
    "tool_subcommand": "direct_append",
    "tool_new": "create_new",
    "permission_relax": "json_edit",
    "permission_tighten": "json_edit",
    "test_stub": "auto_sync",
    "command_missing": "create_new",
    "planner_risk_dimension_missing": "direct_append",
}

# ── YAML 解析 ─────────────────────────────────────────────────────────────────

def parse_yaml_simple(content: str) -> dict:
    result = {}
    current_key = None
    block_mode = None
    block_buf: list = []

    def flush_block():
        if current_key is None:
            return
        if block_mode == "list":
            result[current_key] = block_buf[:]
        elif block_mode == "scalar":
            result[current_key] = "\n".join(block_buf).strip()

    for raw_line in content.splitlines():
        if block_mode is not None:
            stripped = raw_line.strip()
            if block_mode == "list" and re.match(r"^\s+-\s", raw_line):
                block_buf.append(stripped.lstrip("- ").strip().strip("'\""))
                continue
            if block_mode == "scalar" and (raw_line.startswith("  ") or raw_line.startswith("\t")):
                block_buf.append(stripped)
                continue
            flush_block()
            block_mode = None
            block_buf = []

        m = re.match(r"^([\w][\w_-]*):\s*(.*)", raw_line)
        if not m:
            continue

        current_key = m.group(1)
        val = m.group(2).strip()

        if val == "":
            block_mode = "list"
            block_buf = []
        elif val == "|":
            block_mode = "scalar"
            block_buf = []
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1]
            items = [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
            result[current_key] = items
        else:
            result[current_key] = val.strip("'\"")

    flush_block()
    return result


def load_all_candidates() -> list:
    if not CANDIDATES_DIR.exists():
        return []
    candidates = []
    for f in sorted(CANDIDATES_DIR.glob("*.yaml")):
        if f.name in ("SCHEMA.md",):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            data = parse_yaml_simple(content)
            data["_file"] = f
            data["_raw"] = content
            candidates.append(data)
        except Exception:
            pass
    return candidates


def update_candidate_field(filepath: Path, field: str, value: str):
    content = filepath.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{re.escape(field)}:.*$", re.MULTILINE)
    if pattern.search(content):
        new_content = pattern.sub(f"{field}: {value}", content)
    else:
        new_content = content.rstrip("\n") + f"\n{field}: {value}\n"
    filepath.write_text(new_content, encoding="utf-8")


def append_validated_project(filepath: Path, project: str):
    content = filepath.read_text(encoding="utf-8")
    if project in content:
        print(f"  ⚠️  项目 {project} 已在验证列表中")
        return
    new_content = re.sub(
        r"(validated_projects:\s*\n(?:  - .+\n)*)",
        rf"\1  - {project}\n",
        content,
    )
    filepath.write_text(new_content, encoding="utf-8")
    data = parse_yaml_simple(filepath.read_text(encoding="utf-8"))
    validated = data.get("validated_projects", [])
    if isinstance(validated, str):
        validated = [validated]
    count = len(validated)
    new_conf = "low" if count < 2 else ("medium" if count < 3 else "high")
    update_candidate_field(filepath, "confidence", new_conf)


# ── TASK-ANN-03: auto_attach 操作 ────────────────────────────────────────────

def cmd_attach(args):
    """标记候选为 auto_attach: true，使 context-probe 可临时激活它。"""
    candidates = load_all_candidates()
    target = next((c for c in candidates if c.get("id") == args.id), None)
    if not target:
        print(f"❌ 未找到候选：{args.id}")
        sys.exit(1)

    # 安全检查：confidence 必须 >= medium
    confidence = target.get("confidence", "low")
    if confidence == "low" and not args.force:
        print(f"⚠️  候选 {args.id} 的 confidence 为 low（仅1个项目验证），临时激活风险较高。")
        print(f"   若确定要激活，请使用 --force 参数。")
        sys.exit(1)

    update_candidate_field(target["_file"], "auto_attach", "true")
    print(f"✅ {args.id} 已标记为 auto_attach: true")
    print(f"   context-probe 在领域匹配时将自动注入此候选的临时规则")
    print(f"   取消：tracker.py detach {args.id}")


def cmd_detach(args):
    """取消候选的 auto_attach 标记。"""
    candidates = load_all_candidates()
    target = next((c for c in candidates if c.get("id") == args.id), None)
    if not target:
        print(f"❌ 未找到候选：{args.id}")
        sys.exit(1)
    update_candidate_field(target["_file"], "auto_attach", "false")
    print(f"✅ {args.id} 已取消 auto_attach（detach）")


# ── promote 实现 ─────────────────────────────────────────────────────────────

def promote_direct_append(data: dict, filepath: Path) -> bool:
    target = ROOT / data.get("target_file", "")
    if not target.exists():
        print(f"  ❌ 目标文件不存在：{target}")
        return False
    diff_content = data.get("proposed_diff", "").strip()
    if not diff_content:
        print(f"  ❌ proposed_diff 为空，无法自动 promote")
        return False
    candidate_id = data.get("id", filepath.stem)
    today = datetime.now().strftime("%Y-%m-%d")
    addition = f"\n\n<!-- promoted from {candidate_id} on {today} -->\n{diff_content}\n"
    existing = target.read_text(encoding="utf-8")
    target.write_text(existing + addition, encoding="utf-8")
    print(f"  ✅ 已追加到：{target.relative_to(ROOT)}")
    return True


def promote_json_edit(data: dict, filepath: Path) -> bool:
    target = ROOT / data.get("target_file", "settings.local.json")
    proposed = data.get("proposed_diff", "（无内容）")
    print(f"  ℹ️  权限类候选需要人工编辑：{target.relative_to(ROOT)}")
    for line in proposed.splitlines():
        print(f"       {line}")
    return True


def promote_auto_sync(data: dict, filepath: Path) -> bool:
    skill_id = data.get("domain", "")
    if not skill_id:
        target_file = data.get("target_file", "")
        m = re.search(r"test_(\w+)\.py", target_file)
        skill_id = m.group(1) if m else "unknown"
    result = subprocess.run(
        [sys.executable, str(ROOT / ".claude/hooks/test-sync/sync.py"), "--skill", skill_id],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return False
    return True


def promote_create_new(data: dict, filepath: Path) -> bool:
    target = data.get("target_file", "（未指定）")
    proposed = data.get("proposed_diff", "（无内容）")
    print(f"  ℹ️  需要创建新文件：{target}")
    for line in proposed.splitlines()[:10]:
        print(f"       {line}")
    return True


def do_promote(candidate_id: str, confirm: bool = False) -> bool:
    candidates = load_all_candidates()
    target = next((c for c in candidates if c.get("id") == candidate_id), None)
    if not target:
        print(f"❌ 未找到候选：{candidate_id}")
        return False
    status = target.get("status", "")
    if status not in ("approved", "pending_review") and not confirm:
        print(f"⚠️  候选状态为 {status}，请先 approve 或使用 --confirm 强制执行")
        return False
    ctype = target.get("candidate_type", "skill_rule")
    promote_strategy = PROMOTE_TARGETS.get(ctype, "direct_append")
    filepath = target["_file"]
    print(f"\n[skill-tracker] Promoting {candidate_id} ({ctype})")
    success = False
    if promote_strategy == "direct_append":
        success = promote_direct_append(target, filepath)
    elif promote_strategy == "json_edit":
        success = promote_json_edit(target, filepath)
    elif promote_strategy == "auto_sync":
        success = promote_auto_sync(target, filepath)
    elif promote_strategy == "create_new":
        success = promote_create_new(target, filepath)
    if success:
        update_candidate_field(filepath, "status", "promoted")
        update_candidate_field(filepath, "promoted_at", datetime.now().strftime("%Y-%m-%d"))
        # 清除 auto_attach（已正式 promote，不再需要临时激活）
        update_candidate_field(filepath, "auto_attach", "false")
        write_changelog_entry(target)
        # 触发 test-sync
        if ctype in ("skill_rule", "hook_trigger", "hook_check"):
            target_file = target.get("target_file", "")
            skill_m = re.search(r"skills/([^/]+)/SKILL", target_file)
            hook_m = re.search(r"hooks/([^/]+)/HOOK", target_file)
            sid = skill_m or hook_m
            if sid:
                print(f"\n  自动触发 test-sync...")
                subprocess.run(
                    [sys.executable, str(ROOT / ".claude/hooks/test-sync/sync.py"),
                     "--skill", sid.group(1)],
                    check=False,
                )
    return success


def write_changelog_entry(data: dict):
    if not CHANGELOG.exists():
        CHANGELOG.write_text("# Skill Changelog\n\n", encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    target = data.get("target_file", "unknown")
    rule = data.get("proposed_rule", "（未指定）")
    cid = data.get("id", "unknown")
    projects = data.get("validated_projects", [])
    if isinstance(projects, str):
        projects = [projects]
    entry = f"""
## {target} — {today}
- 来源候选：`{cid}`
- 规则：{rule}
- 验证项目：{', '.join(projects)}
- 类型：{data.get('candidate_type', 'unknown')}
- 审核：人工批准
"""
    existing = CHANGELOG.read_text(encoding="utf-8")
    CHANGELOG.write_text(existing + entry, encoding="utf-8")


# ── 子命令实现 ────────────────────────────────────────────────────────────────

def cmd_candidates(args):
    candidates = load_all_candidates()

    # 过滤条件
    if args.type and args.type != "all":
        candidates = [c for c in candidates if c.get("candidate_type") == args.type]
    if args.min_validated:
        candidates = [
            c for c in candidates
            if len(c.get("validated_projects", [])) >= args.min_validated
            if isinstance(c.get("validated_projects", []), list)
        ]
    if args.status:
        candidates = [c for c in candidates if c.get("status") == args.status]

    # TASK-ANN-03: --auto-attach 过滤
    if getattr(args, "auto_attach", False):
        candidates = [c for c in candidates if str(c.get("auto_attach", "false")).lower() == "true"]

    # TASK-ANN-03: --domain 过滤
    if getattr(args, "domain", None):
        candidates = [c for c in candidates if c.get("domain") == args.domain]

    if not candidates:
        print("  （无匹配候选）")
        return

    pending = [c for c in candidates if c.get("status") == "pending_review"]
    approved = [c for c in candidates if c.get("status") == "approved"]
    promoted = [c for c in candidates if c.get("status") == "promoted"]

    print(f"\n📋 候选摘要  pending:{len(pending)}  approved:{len(approved)}  promoted:{len(promoted)}")
    print(f"{'─'*60}")

    if pending:
        print(f"\n  [待审核]")
        for c in pending:
            conf_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(c.get("confidence", "low"), "⚪")
            # TASK-ANN-03: 显示 auto_attach 状态
            attach_icon = "📎" if str(c.get("auto_attach", "false")).lower() == "true" else "  "
            validated = c.get("validated_projects", [])
            vcount = len(validated) if isinstance(validated, list) else 1
            print(f"  {conf_icon}{attach_icon} {c.get('id','?'):<30} → {c.get('target_file','?')}")
            print(f"      {c.get('proposed_rule','')[:55]}")
            print(f"      验证项目数: {vcount}  |  类型: {c.get('candidate_type','?')}  |  auto_attach: {c.get('auto_attach','false')}")

    if approved:
        print(f"\n  [已批准，待 promote]")
        for c in approved:
            print(f"  ✅ {c.get('id','?')} → {c.get('target_file','?')}")


def cmd_validate(args):
    candidates = load_all_candidates()
    target = next((c for c in candidates if c.get("id") == args.id), None)
    if not target:
        print(f"❌ 未找到候选：{args.id}")
        sys.exit(1)
    append_validated_project(target["_file"], args.project)
    data = parse_yaml_simple(target["_file"].read_text(encoding="utf-8"))
    print(f"✅ {args.id} 追加验证项目：{args.project}")
    print(f"   当前验证项目：{data.get('validated_projects', [])}")
    print(f"   当前置信度：{data.get('confidence', '?')}")


def cmd_approve(args):
    candidates = load_all_candidates()
    target = next((c for c in candidates if c.get("id") == args.id), None)
    if not target:
        print(f"❌ 未找到候选：{args.id}")
        sys.exit(1)
    update_candidate_field(target["_file"], "status", "approved")
    print(f"✅ {args.id} 已标记为 approved")


def cmd_reject(args):
    candidates = load_all_candidates()
    target = next((c for c in candidates if c.get("id") == args.id), None)
    if not target:
        print(f"❌ 未找到候选：{args.id}")
        sys.exit(1)
    update_candidate_field(target["_file"], "status", "rejected")
    # 拒绝时同时清除 auto_attach
    update_candidate_field(target["_file"], "auto_attach", "false")
    if args.reason:
        content = target["_file"].read_text(encoding="utf-8")
        target["_file"].write_text(content + f"\nreject_reason: {args.reason}\n", encoding="utf-8")
    print(f"✅ {args.id} 已标记为 rejected：{args.reason or '（无原因）'}")


def cmd_promote(args):
    do_promote(args.id, confirm=getattr(args, "confirm", False))


def cmd_status(args):
    candidates = load_all_candidates()
    total = len(candidates)
    by_type = {}
    by_status = {}
    attached = sum(1 for c in candidates if str(c.get("auto_attach", "false")).lower() == "true")
    for c in candidates:
        t = c.get("candidate_type", "unknown")
        s = c.get("status", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_status[s] = by_status.get(s, 0) + 1

    print(f"\n📊 候选库状态")
    print(f"{'─'*40}")
    print(f"  总计：{total} 条  |  临时激活 (auto_attach)：{attached} 条")
    print(f"\n  按状态：")
    for s, n in sorted(by_status.items()):
        print(f"    {s:<20} {n}")
    print(f"\n  按类型：")
    for t, n in sorted(by_type.items()):
        print(f"    {t:<30} {n}")


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Skill Tracker — 框架改进候选管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  管理 Meta-Skill Loop 生成的候选规则。attach/detach 配合 context-probe 实现
  候选临时激活，消除从"发现"到"实用"的等待期。

示例:
  python3 tracker.py candidates --min-validated 2
  python3 tracker.py attach HOOK_CAND_SDD-TINYHTTPD_001
  python3 tracker.py candidates --auto-attach --status pending_review --domain network_code
  python3 tracker.py detach HOOK_CAND_SDD-TINYHTTPD_001
  python3 tracker.py approve HOOK_CAND_SDD-TINYHTTPD_001
  python3 tracker.py promote HOOK_CAND_SDD-TINYHTTPD_001
""",
    )
    subparsers = parser.add_subparsers(dest="cmd")

    # candidates
    cand_p = subparsers.add_parser("candidates", help="查看候选列表")
    cand_p.add_argument("--type", default="all", help="候选类型过滤")
    cand_p.add_argument("--min-validated", type=int, default=0, dest="min_validated",
                        help="最少验证项目数")
    cand_p.add_argument("--status", default=None, help="按状态过滤")
    # TASK-ANN-03: 新增过滤参数
    cand_p.add_argument("--auto-attach", action="store_true", dest="auto_attach",
                        help="只显示 auto_attach: true 的候选")
    cand_p.add_argument("--domain", default=None,
                        help="按 domain 过滤（如 network_code、tdd_patterns）")

    # TASK-ANN-03: attach / detach
    att_p = subparsers.add_parser(
        "attach",
        help="将候选标记为 auto_attach: true（context-probe 会临时注入其规则）",
    )
    att_p.add_argument("id", help="候选 ID")
    att_p.add_argument("--force", action="store_true",
                       help="强制附加 confidence=low 的候选（不推荐）")

    det_p = subparsers.add_parser("detach", help="取消候选的 auto_attach 标记")
    det_p.add_argument("id", help="候选 ID")

    # validate
    val_p = subparsers.add_parser("validate", help="追加验证项目")
    val_p.add_argument("id", help="候选 ID")
    val_p.add_argument("--project", required=True, help="项目名称")

    # approve / reject / promote
    app_p = subparsers.add_parser("approve", help="批准候选")
    app_p.add_argument("id", help="候选 ID")

    rej_p = subparsers.add_parser("reject", help="拒绝候选")
    rej_p.add_argument("id", help="候选 ID")
    rej_p.add_argument("--reason", default="", help="拒绝原因")

    pro_p = subparsers.add_parser("promote", help="提升候选到目标文件")
    pro_p.add_argument("id", help="候选 ID")
    pro_p.add_argument("--confirm", action="store_true", help="强制执行（跳过状态检查）")

    # status
    subparsers.add_parser("status", help="候选库总体统计")

    args = parser.parse_args()

    dispatch = {
        "candidates": cmd_candidates,
        "attach": cmd_attach,
        "detach": cmd_detach,
        "validate": cmd_validate,
        "approve": cmd_approve,
        "reject": cmd_reject,
        "promote": cmd_promote,
        "status": cmd_status,
    }

    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
