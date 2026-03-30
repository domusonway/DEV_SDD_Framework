#!/usr/bin/env python3
"""
skill-tracker/tracker.py
全类型框架改进候选的跨项目追踪与提升工具

用法:
  python3 .claude/tools/skill-tracker/tracker.py candidates            # 查看全部候选
  python3 .claude/tools/skill-tracker/tracker.py candidates --type hook_trigger
  python3 .claude/tools/skill-tracker/tracker.py candidates --min-validated 2
  python3 .claude/tools/skill-tracker/tracker.py validate <id> --project <p>  # 追加验证
  python3 .claude/tools/skill-tracker/tracker.py approve <id>          # 标记待提升
  python3 .claude/tools/skill-tracker/tracker.py reject <id> --reason "..."
  python3 .claude/tools/skill-tracker/tracker.py promote <id>          # 人工批准后写入目标文件
  python3 .claude/tools/skill-tracker/tracker.py status                # 候选统计摘要
"""
import sys
import re
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

# candidate_type → 提升目标目录/文件的解析规则
PROMOTE_TARGETS = {
    "skill_rule": "direct_append",       # 追加到 target_file
    "hook_trigger": "direct_append",     # 追加到 target_file
    "hook_check": "direct_append",
    "agent_constraint": "direct_append",
    "agent_role_gap": "create_new",      # 需要创建新文件
    "tool_subcommand": "direct_append",
    "tool_new": "create_new",
    "permission_relax": "json_edit",     # 编辑 JSON
    "permission_tighten": "json_edit",
    "test_stub": "auto_sync",            # 调用 test-sync
    "command_missing": "create_new",
}


# ── YAML 解析（轻量，不依赖 PyYAML）─────────────────────────────────────────
def parse_yaml_simple(content: str) -> dict:
    """
    解析候选 YAML 文件，支持：
      - 标量：key: value
      - 行内列表：key: [a, b, c]
      - block list：key:\n  - a\n  - b
      - block scalar (|)：key: |\n  line1\n  line2
    """
    result = {}
    current_key = None
    block_mode = None   # "scalar" | "list"
    block_buf: list = []

    def flush_block():
        if current_key is None:
            return
        if block_mode == "list":
            result[current_key] = block_buf[:]
        elif block_mode == "scalar":
            result[current_key] = "\n".join(block_buf).strip()

    for raw_line in content.splitlines():
        # ── 在 block 模式中处理缩进行 ──────────────────────────────────
        if block_mode is not None:
            stripped = raw_line.strip()
            # block list 项：以 "- " 开头的缩进行
            if block_mode == "list" and re.match(r"^\s+-\s", raw_line):
                block_buf.append(stripped.lstrip("- ").strip().strip("'\""))
                continue
            # block scalar 行：缩进行
            if block_mode == "scalar" and (raw_line.startswith("  ") or raw_line.startswith("\t")):
                block_buf.append(stripped)
                continue
            # 否则：block 结束，flush 后继续解析当前行
            flush_block()
            block_mode = None
            block_buf = []

        # ── 顶层 key: value 行 ──────────────────────────────────────────
        m = re.match(r"^([\w][\w_-]*):\s*(.*)", raw_line)
        if not m:
            continue

        current_key = m.group(1)
        val = m.group(2).strip()

        if val == "":
            # 下一行是 block（list 或 scalar）
            block_mode = "list"   # 默认猜 list，遇到非 "- " 行时会降级
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


def load_all_candidates() -> list[dict]:
    """加载 candidates/ 目录下全部 YAML 候选"""
    if not CANDIDATES_DIR.exists():
        return []
    candidates = []
    for f in sorted(CANDIDATES_DIR.glob("*.yaml")):
        if f.name == "SCHEMA.md":
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
    """更新 YAML 文件中的单个字段；字段不存在时追加到文件末尾"""
    content = filepath.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{re.escape(field)}:.*$", re.MULTILINE)
    if pattern.search(content):
        new_content = pattern.sub(f"{field}: {value}", content)
    else:
        new_content = content.rstrip("\n") + f"\n{field}: {value}\n"
    filepath.write_text(new_content, encoding="utf-8")


def append_validated_project(filepath: Path, project: str):
    """在 validated_projects 列表中追加新项目"""
    content = filepath.read_text(encoding="utf-8")
    if project in content:
        print(f"  ⚠️  项目 {project} 已在验证列表中")
        return

    # 在列表末尾追加
    new_content = re.sub(
        r"(validated_projects:\s*\n(?:  - .+\n)*)",
        rf"\1  - {project}\n",
        content,
    )
    filepath.write_text(new_content, encoding="utf-8")

    # 更新验证数并提升 confidence
    data = parse_yaml_simple(new_content)
    validated = data.get("validated_projects", [])
    if isinstance(validated, str):
        validated = [validated]
    count = len(validated)
    new_conf = "low" if count < 2 else ("medium" if count < 3 else "high")
    update_candidate_field(filepath, "confidence", new_conf)


# ── promote 实现 ─────────────────────────────────────────────────────────────
def promote_direct_append(data: dict, filepath: Path) -> bool:
    """将 proposed_diff 追加到目标文件末尾（带标注）"""
    target = ROOT / data.get("target_file", "")
    if not target.exists():
        print(f"  ❌ 目标文件不存在：{target}")
        return False

    diff_content = data.get("proposed_diff", "").strip()
    if not diff_content:
        print(f"  ❌ proposed_diff 为空，无法自动 promote")
        print(f"     请手动编辑：{target}")
        return False

    candidate_id = data.get("id", filepath.stem)
    today = datetime.now().strftime("%Y-%m-%d")
    addition = f"\n\n<!-- promoted from {candidate_id} on {today} -->\n{diff_content}\n"

    existing = target.read_text(encoding="utf-8")
    target.write_text(existing + addition, encoding="utf-8")
    print(f"  ✅ 已追加到：{target.relative_to(ROOT)}")
    return True


def promote_json_edit(data: dict, filepath: Path) -> bool:
    """提示人工编辑 JSON 文件（不自动修改，因为 deny 规则变更风险高）"""
    target = ROOT / data.get("target_file", "settings.local.json")
    proposed = data.get("proposed_diff", "（无内容）")
    print(f"  ℹ️  权限类候选需要人工编辑：{target.relative_to(ROOT)}")
    print(f"     建议修改内容：")
    for line in proposed.splitlines():
        print(f"       {line}")
    print(f"     注意：权限修改不自动执行，请手动编辑后运行 verify-rules/check.sh 验证")
    return True  # 标记为 promoted（人工执行），不报错


def promote_auto_sync(data: dict, filepath: Path) -> bool:
    """调用 test-sync/sync.py 追加测试桩"""
    skill_id = data.get("domain", "")
    if not skill_id:
        target_file = data.get("target_file", "")
        m = re.search(r"test_(\w+)\.py", target_file)
        skill_id = m.group(1) if m else "unknown"

    result = subprocess.run(
        [sys.executable, str(ROOT / ".claude/hooks/test-sync/sync.py"), "--skill", skill_id],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return False
    return True


def promote_create_new(data: dict, filepath: Path) -> bool:
    """提示人工创建新文件"""
    target = data.get("target_file", "（未指定）")
    proposed = data.get("proposed_diff", "（无内容）")
    print(f"  ℹ️  需要创建新文件：{target}")
    print(f"     建议内容：")
    for line in proposed.splitlines()[:10]:
        print(f"       {line}")
    if len(proposed.splitlines()) > 10:
        print(f"       ... （共 {len(proposed.splitlines())} 行，见候选文件）")
    print(f"     请手动创建后更新候选状态：tracker.py promote {data.get('id')} --confirm")
    return True


def do_promote(candidate_id: str, confirm: bool = False) -> bool:
    """执行 promote 操作"""
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

        # 写入 changelog
        write_changelog_entry(target)

        # 触发 test-sync（如果是 skill/hook 类型）
        if ctype in ("skill_rule", "hook_trigger", "hook_check"):
            target_file = target.get("target_file", "")
            skill_m = re.search(r"skills/([^/]+)/SKILL", target_file)
            hook_m = re.search(r"hooks/([^/]+)/HOOK", target_file)
            sid = (skill_m or hook_m)
            if sid:
                print(f"\n  自动触发 test-sync...")
                subprocess.run(
                    [sys.executable, str(ROOT / ".claude/hooks/test-sync/sync.py"),
                     "--skill", sid.group(1)],
                    check=False,
                )

    return success


def write_changelog_entry(data: dict):
    """写入 skill-changelog.md"""
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

    # 过滤
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

    if not candidates:
        print("  （无匹配候选）")
        return

    # 按 status 分组
    pending = [c for c in candidates if c.get("status") == "pending_review"]
    approved = [c for c in candidates if c.get("status") == "approved"]
    promoted = [c for c in candidates if c.get("status") == "promoted"]

    print(f"\n📋 候选摘要  pending:{len(pending)}  approved:{len(approved)}  promoted:{len(promoted)}")
    print(f"{'─'*60}")

    if pending:
        print(f"\n  [待审核]")
        for c in pending:
            conf_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(c.get("confidence", "low"), "⚪")
            validated = c.get("validated_projects", [])
            vcount = len(validated) if isinstance(validated, list) else 1
            print(f"  {conf_icon} {c.get('id','?'):<30} → {c.get('target_file','?')}")
            print(f"      {c.get('proposed_rule','')[:55]}")
            print(f"      验证项目数: {vcount}  |  类型: {c.get('candidate_type','?')}")

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
    print(f"   执行 promote：python3 .claude/tools/skill-tracker/tracker.py promote {args.id}")


def cmd_reject(args):
    candidates = load_all_candidates()
    target = next((c for c in candidates if c.get("id") == args.id), None)
    if not target:
        print(f"❌ 未找到候选：{args.id}")
        sys.exit(1)
    update_candidate_field(target["_file"], "status", "rejected")
    if args.reason:
        content = target["_file"].read_text(encoding="utf-8")
        target["_file"].write_text(
            content + f"\nreject_reason: {args.reason}\n", encoding="utf-8"
        )
    print(f"✅ {args.id} 已标记为 rejected：{args.reason or '（无原因）'}")


def cmd_promote(args):
    do_promote(args.id, confirm=getattr(args, "confirm", False))


def cmd_status(args):
    candidates = load_all_candidates()
    total = len(candidates)
    by_type = {}
    by_status = {}
    for c in candidates:
        t = c.get("candidate_type", "unknown")
        s = c.get("status", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_status[s] = by_status.get(s, 0) + 1

    print(f"\n📊 候选库状态")
    print(f"{'─'*40}")
    print(f"  总计：{total} 条")
    print(f"\n  按状态：")
    for s, n in sorted(by_status.items()):
        print(f"    {s:<20} {n}")
    print(f"\n  按类型：")
    for t, n in sorted(by_type.items()):
        print(f"    {t:<30} {n}")


def main():
    parser = argparse.ArgumentParser(description="Skill Tracker — 框架改进候选管理")
    subparsers = parser.add_subparsers(dest="cmd")

    # candidates
    cand_p = subparsers.add_parser("candidates", help="查看候选列表")
    cand_p.add_argument("--type", default="all", help="候选类型过滤")
    cand_p.add_argument("--min-validated", type=int, default=0, help="最少验证项目数")
    cand_p.add_argument("--status", default=None, help="按状态过滤")

    # validate
    val_p = subparsers.add_parser("validate", help="追加验证项目")
    val_p.add_argument("id", help="候选 ID")
    val_p.add_argument("--project", required=True, help="项目名称")

    # approve
    app_p = subparsers.add_parser("approve", help="批准候选")
    app_p.add_argument("id", help="候选 ID")

    # reject
    rej_p = subparsers.add_parser("reject", help="拒绝候选")
    rej_p.add_argument("id", help="候选 ID")
    rej_p.add_argument("--reason", default="", help="拒绝原因")

    # promote
    pro_p = subparsers.add_parser("promote", help="提升候选到目标文件")
    pro_p.add_argument("id", help="候选 ID")
    pro_p.add_argument("--confirm", action="store_true", help="强制执行（跳过状态检查）")

    # status
    subparsers.add_parser("status", help="候选库总体统计")

    args = parser.parse_args()

    dispatch = {
        "candidates": cmd_candidates,
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
        sys.exit(1)


if __name__ == "__main__":
    main()
