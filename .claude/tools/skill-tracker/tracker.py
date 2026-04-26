#!/usr/bin/env python3
from __future__ import annotations

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

REQUIRED_CANDIDATE_FIELDS = [
    "id",
    "candidate_type",
    "source_project",
    "observed_evidence",
    "proposed_rule",
    "target_file",
    "proposed_diff",
    "confidence",
    "validated_projects",
    "status",
    "created",
]

KNOWN_STATUSES = {
    "pending_review",
    "approved",
    "rejected",
    "promoted",
    "deferred",
    "archived",
    "project_only",
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


def append_candidate_audit(filepath: Path, action: str, detail: str = ""):
    today = datetime.now().strftime("%Y-%m-%d")
    content = filepath.read_text(encoding="utf-8")
    audit_line = f"\nreview_history:\n  - {today}: {action}{(' - ' + detail) if detail else ''}\n"
    if "review_history:" in content:
        audit_line = f"  - {today}: {action}{(' - ' + detail) if detail else ''}\n"
    filepath.write_text(content.rstrip("\n") + "\n" + audit_line, encoding="utf-8")


def validate_candidate_record(data: dict) -> list[str]:
    errors = []
    for field in REQUIRED_CANDIDATE_FIELDS:
        value = data.get(field)
        if value in (None, "", []):
            errors.append(f"missing:{field}")
    status = data.get("status")
    if status and status not in KNOWN_STATUSES:
        errors.append(f"invalid_status:{status}")
    confidence = data.get("confidence")
    if confidence and confidence not in {"low", "medium", "high"}:
        errors.append(f"invalid_confidence:{confidence}")
    validated = data.get("validated_projects", [])
    if isinstance(validated, str):
        validated_count = 1 if validated else 0
    elif isinstance(validated, list):
        validated_count = len(validated)
    else:
        validated_count = 0
    expected_confidence = "low" if validated_count < 2 else ("medium" if validated_count < 3 else "high")
    if confidence in {"low", "medium", "high"} and confidence != expected_confidence:
        errors.append(f"confidence_mismatch:{confidence}_expected_{expected_confidence}_for_{validated_count}_projects")
    return errors


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
    marker_begin = f"<!-- DEV_SDD:PROMOTE:BEGIN id={candidate_id} date={today} -->"
    marker_end = f"<!-- DEV_SDD:PROMOTE:END id={candidate_id} -->"
    addition = f"\n\n{marker_begin}\n{diff_content}\n{marker_end}\n"
    existing = target.read_text(encoding="utf-8")
    target.write_text(existing + addition, encoding="utf-8")
    update_candidate_field(filepath, "promote_strategy", "direct_append_marked")
    update_candidate_field(filepath, "rollback_marker_begin", f"'{marker_begin}'")
    update_candidate_field(filepath, "rollback_marker_end", f"'{marker_end}'")
    update_candidate_field(filepath, "promoted_target", str(target.relative_to(ROOT)))
    print(f"  ✅ 已追加到：{target.relative_to(ROOT)}")
    print(f"  ↩ rollback marker: {marker_begin} ... {marker_end}")
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
        append_candidate_audit(filepath, "promote", f"strategy={promote_strategy}")
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
- 回滚：若为 direct_append_marked，删除目标文件中 `DEV_SDD:PROMOTE:BEGIN id={cid}` 到 `DEV_SDD:PROMOTE:END id={cid}` 的块
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
    append_candidate_audit(target["_file"], "approve")
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
    append_candidate_audit(target["_file"], "reject", args.reason or "")
    print(f"✅ {args.id} 已标记为 rejected：{args.reason or '（无原因）'}")


def _set_lifecycle_status(args, status: str, field_name: str, success_label: str):
    candidates = load_all_candidates()
    target = next((c for c in candidates if c.get("id") == args.id), None)
    if not target:
        print(f"❌ 未找到候选：{args.id}")
        sys.exit(1)
    update_candidate_field(target["_file"], "status", status)
    if getattr(args, "reason", ""):
        update_candidate_field(target["_file"], field_name, args.reason)
    if status in {"archived", "project_only"}:
        update_candidate_field(target["_file"], "auto_attach", "false")
    append_candidate_audit(target["_file"], status, getattr(args, "reason", "") or "")
    print(f"✅ {args.id} 已标记为 {success_label}: {getattr(args, 'reason', '') or '（无原因）'}")


def cmd_defer(args):
    _set_lifecycle_status(args, "deferred", "defer_reason", "deferred")


def cmd_archive(args):
    _set_lifecycle_status(args, "archived", "archive_reason", "archived")


def cmd_project_only(args):
    _set_lifecycle_status(args, "project_only", "project_only_reason", "project_only")


def cmd_validate_schema(args):
    candidates = load_all_candidates()
    invalid = []
    for candidate in candidates:
        errors = validate_candidate_record(candidate)
        if errors:
            invalid.append({
                "id": candidate.get("id") or candidate.get("_file").stem,
                "file": str(candidate.get("_file").relative_to(ROOT)),
                "errors": errors,
            })
    status = "ok" if not invalid else "error"
    payload = {
        "status": status,
        "message": "candidate schema 校验通过" if not invalid else f"{len(invalid)} 个候选 schema 异常",
        "data": {"total": len(candidates), "invalid": invalid},
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(payload["message"])
    for item in invalid:
        print(f"  - {item['id']}: {', '.join(item['errors'])}")


def cmd_rollback_info(args):
    candidates = load_all_candidates()
    target = next((c for c in candidates if c.get("id") == args.id), None)
    if not target:
        print(f"❌ 未找到候选：{args.id}")
        sys.exit(1)
    data = {
        "id": target.get("id"),
        "status": target.get("status"),
        "promoted_target": target.get("promoted_target") or target.get("target_file"),
        "promote_strategy": target.get("promote_strategy", "unknown"),
        "rollback_marker_begin": target.get("rollback_marker_begin", ""),
        "rollback_marker_end": target.get("rollback_marker_end", ""),
        "manual_instruction": "Remove the marked DEV_SDD:PROMOTE block from promoted_target; do not use destructive git reset.",
    }
    if getattr(args, "json", False):
        print(json.dumps({"status": "ok", "message": "rollback info", "data": data}, ensure_ascii=False, indent=2))
        return
    print(f"候选: {data['id']}")
    print(f"目标: {data['promoted_target']}")
    print(f"策略: {data['promote_strategy']}")
    print(f"begin: {data['rollback_marker_begin']}")
    print(f"end: {data['rollback_marker_end']}")


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


def _recommend_review_action(candidate: dict) -> str:
    status = candidate.get("status", "pending_review")
    if status != "pending_review":
        return "none"
    confidence = candidate.get("confidence", "low")
    validated = candidate.get("validated_projects", [])
    vcount = len(validated) if isinstance(validated, list) else (1 if validated else 0)
    if confidence == "high" or vcount >= 3:
        return "approve_or_promote"
    if confidence == "medium" or vcount >= 2:
        return "review_or_attach_temp"
    return "defer_until_more_evidence"


def cmd_review_summary(args):
    candidates = load_all_candidates()
    rows = []
    for candidate in candidates:
        rows.append({
            "id": candidate.get("id"),
            "status": candidate.get("status"),
            "candidate_type": candidate.get("candidate_type"),
            "confidence": candidate.get("confidence"),
            "source_project": candidate.get("source_project"),
            "target_file": candidate.get("target_file"),
            "recommendation": _recommend_review_action(candidate),
        })
    by_recommendation: dict[str, int] = {}
    for row in rows:
        key = row["recommendation"] or "none"
        by_recommendation[key] = by_recommendation.get(key, 0) + 1
    payload = {
        "total": len(rows),
        "by_recommendation": by_recommendation,
        "items": rows,
    }
    if getattr(args, "json", False):
        print(json.dumps({"status": "ok", "message": "candidate review summary", "data": payload}, ensure_ascii=False, indent=2))
        return
    print("candidate review summary")
    for row in rows:
        print(f"  - {row['id']} [{row['confidence']}] → {row['recommendation']}")


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

    defer_p = subparsers.add_parser("defer", help="暂缓候选，等待更多证据")
    defer_p.add_argument("id", help="候选 ID")
    defer_p.add_argument("--reason", default="", help="暂缓原因")

    archive_p = subparsers.add_parser("archive", help="归档候选，不再参与审核")
    archive_p.add_argument("id", help="候选 ID")
    archive_p.add_argument("--reason", default="", help="归档原因")

    project_only_p = subparsers.add_parser("project-only", help="标记候选仅适用于来源项目")
    project_only_p.add_argument("id", help="候选 ID")
    project_only_p.add_argument("--reason", default="", help="项目限定原因")

    schema_p = subparsers.add_parser("validate-schema", help="校验候选 schema 健康度")
    schema_p.add_argument("--json", action="store_true", help="输出 JSON envelope")

    rollback_p = subparsers.add_parser("rollback-info", help="显示候选 promote 的回滚标记与人工回滚说明")
    rollback_p.add_argument("id", help="候选 ID")
    rollback_p.add_argument("--json", action="store_true", help="输出 JSON envelope")

    # status
    subparsers.add_parser("status", help="候选库总体统计")
    review_summary_p = subparsers.add_parser("review-summary", help="输出候选审核建议摘要")
    review_summary_p.add_argument("--json", action="store_true", help="输出 JSON envelope")

    args = parser.parse_args()

    dispatch = {
        "candidates": cmd_candidates,
        "attach": cmd_attach,
        "detach": cmd_detach,
        "validate": cmd_validate,
        "approve": cmd_approve,
        "reject": cmd_reject,
        "promote": cmd_promote,
        "defer": cmd_defer,
        "archive": cmd_archive,
        "project-only": cmd_project_only,
        "validate-schema": cmd_validate_schema,
        "rollback-info": cmd_rollback_info,
        "status": cmd_status,
        "review-summary": cmd_review_summary,
    }

    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
