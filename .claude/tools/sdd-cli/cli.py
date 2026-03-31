#!/usr/bin/env python3
"""
sdd-cli/cli.py
DEV SDD Framework — Agent-First 规则检索与标注 CLI

用法:
  python3 .claude/tools/sdd-cli/cli.py search <keyword> [--json]
  python3 .claude/tools/sdd-cli/cli.py get <id> [--summary] [--json]
  python3 .claude/tools/sdd-cli/cli.py get <id>@<version> [--json]
  python3 .claude/tools/sdd-cli/cli.py get <id> --all-versions [--json]
  python3 .claude/tools/sdd-cli/cli.py list [--type skill|hook|agent|memory] [--json]
  python3 .claude/tools/sdd-cli/cli.py annotate <id> "<annotation>" [--json]
  python3 .claude/tools/sdd-cli/cli.py index [--json]

用途:
  让 Agent 能通过工具调用按语义查找框架规则，而不是依赖 CLAUDE.md 中的硬编码路径。
  所有命令支持 --json flag，输出机器友好的结构化数据供 Agent 解析。

示例:
  # 按关键词搜索
  python3 .claude/tools/sdd-cli/cli.py search asyncio
  python3 .claude/tools/sdd-cli/cli.py search "网络" --json

  # 获取规则全文
  python3 .claude/tools/sdd-cli/cli.py get tdd-cycle
  python3 .claude/tools/sdd-cli/cli.py get network-guard --summary

  # 获取历史版本
  python3 .claude/tools/sdd-cli/cli.py get tdd-cycle@1.0.0
  python3 .claude/tools/sdd-cli/cli.py get tdd-cycle --all-versions

  # 标注规则（持久化经验）
  python3 .claude/tools/sdd-cli/cli.py annotate network-guard "asyncio 代码同样需要触发此 hook"

  # 刷新注册表索引
  python3 .claude/tools/sdd-cli/cli.py index
"""

import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path


# ── 工具函数 ─────────────────────────────────────────────────────────────────

def find_framework_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    # fallback: 从 cwd 向上找
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return Path.cwd()


ROOT = find_framework_root()
REGISTRY_PATH = ROOT / "memory" / "registry.json"
VERSIONS_DIR = ROOT / "memory" / "versions"

STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_WARNING = "warning"


def out(data: dict, as_json: bool):
    """统一输出函数：--json 时输出 JSON，否则输出人类友好文本。"""
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        status = data.get("status", STATUS_OK)
        icon = {"ok": "✅", "error": "❌", "warning": "⚠️"}.get(status, "ℹ️")
        msg = data.get("message", "")
        if msg:
            print(f"{icon}  {msg}")
        payload = data.get("data")
        if payload is not None:
            _print_payload(payload)


def _print_payload(payload):
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                _print_record(item)
            else:
                print(f"  {item}")
    elif isinstance(payload, dict):
        _print_record(payload)
    elif isinstance(payload, str):
        print(payload)


def _print_record(item: dict):
    cid = item.get("id", "?")
    title = item.get("title", item.get("text", ""))
    itype = item.get("type", "")
    path = item.get("path", "")
    version = item.get("version", "")
    ver_str = f"  v{version}" if version else ""
    print(f"  [{itype:<8}] {cid:<32}{ver_str}")
    if title:
        print(f"             {title}")
    if path:
        print(f"             📄 {path}")


def error_out(message: str, as_json: bool, code: int = 1):
    out({"status": STATUS_ERROR, "message": message, "data": None}, as_json)
    sys.exit(code)


# ── 注册表 ────────────────────────────────────────────────────────────────────

# 扫描目标：(glob_pattern, type_label)
SCAN_TARGETS = [
    (".claude/skills/*/SKILL.md", "skill"),
    (".claude/hooks/*/HOOK.md", "hook"),
    (".claude/agents/*.md", "agent"),
    ("memory/important/*.md", "memory"),
    ("memory/critical/*.md", "memory"),
    ("memory/domains/**/INDEX.md", "memory"),
]


def _extract_frontmatter(content: str) -> dict:
    """从文件内容提取 YAML frontmatter（---...---），返回解析字典。"""
    fm = {}
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return fm
    end = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end == -1:
        return fm
    for line in lines[1:end]:
        m = re.match(r"^([\w_-]+):\s*(.*)$", line.strip())
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"\'')
    return fm


def _extract_title(content: str, path: Path) -> str:
    """从文件内容提取标题：优先 frontmatter title，其次第一个 # 标题，最后用文件名。"""
    fm = _extract_frontmatter(content)
    if fm.get("title"):
        return fm["title"]
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            # 去掉 # 前缀和常见角色标注
            title = line[2:].strip()
            title = re.sub(r"^(SKILL:|HOOK:|Agent:)\s*", "", title).strip()
            if title:
                return title
    return path.stem


def _extract_tags(content: str) -> list:
    """从文件内容提取关键标签（用于 search 匹配）。"""
    tags = []
    # 从 frontmatter tags 字段
    fm = _extract_frontmatter(content)
    raw_tags = fm.get("tags", "")
    if raw_tags:
        tags += [t.strip() for t in raw_tags.split(",") if t.strip()]
    # 从内容中提取常见技术词
    tech_keywords = [
        "socket", "recv", "send", "asyncio", "aiohttp", "websocket",
        "http", "tcp", "tdd", "red", "green", "memory", "bytes", "str",
        "threading", "concurrent", "hook", "skill", "agent", "候选", "规则",
        "网络", "测试", "诊断", "bug", "refactor", "validate",
    ]
    content_lower = content.lower()
    for kw in tech_keywords:
        if kw in content_lower and kw not in tags:
            tags.append(kw)
    return tags[:20]


def build_registry() -> dict:
    """扫描框架目录，构建完整注册表。"""
    entries = {}
    for pattern, type_label in SCAN_TARGETS:
        for fpath in sorted(ROOT.glob(pattern)):
            if "__pycache__" in str(fpath):
                continue
            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception:
                continue
            fm = _extract_frontmatter(content)
            # id 推导：优先 frontmatter id，其次目录名
            eid = fm.get("id") or fpath.parent.name
            # 去重：同 id 保留路径更短的（通常是主文件）
            if eid in entries:
                existing_depth = len(Path(entries[eid]["path"]).parts)
                new_depth = len(fpath.relative_to(ROOT).parts)
                if new_depth >= existing_depth:
                    continue
            rel_path = str(fpath.relative_to(ROOT))
            entry = {
                "id": eid,
                "type": type_label,
                "path": rel_path,
                "title": _extract_title(content, fpath),
                "tags": _extract_tags(content),
                "version": fm.get("version", ""),
                "recommended": fm.get("recommended", "true").lower() != "false",
                "created": fm.get("created", ""),
                "last_updated": fm.get("last_updated",
                                       datetime.fromtimestamp(fpath.stat().st_mtime).strftime("%Y-%m-%d")),
            }
            entries[eid] = entry
    return {
        "generated_at": datetime.now().isoformat(),
        "framework_root": str(ROOT),
        "entries": list(entries.values()),
    }


def load_registry() -> dict:
    """加载注册表，若不存在则自动构建。"""
    if not REGISTRY_PATH.exists():
        reg = build_registry()
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2))
        return reg
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return build_registry()


# ── 子命令实现 ────────────────────────────────────────────────────────────────

def cmd_index(args):
    """sdd index — 重新扫描并写入 registry.json。"""
    reg = build_registry()
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2))
    count = len(reg["entries"])
    out({
        "status": STATUS_OK,
        "message": f"注册表已更新，共 {count} 条规则 → {REGISTRY_PATH.relative_to(ROOT)}",
        "data": {"count": count, "path": str(REGISTRY_PATH.relative_to(ROOT))},
    }, args.json)


def cmd_search(args):
    """sdd search <keyword> — 模糊搜索规则。"""
    keyword = args.keyword.lower()
    reg = load_registry()
    matches = []
    for entry in reg.get("entries", []):
        score = 0
        # id 精确匹配得分最高
        if keyword in entry["id"].lower():
            score += 10
        # title 匹配
        if keyword in entry["title"].lower():
            score += 5
        # tags 匹配
        for tag in entry.get("tags", []):
            if keyword in tag.lower():
                score += 2
                break
        if score > 0:
            matches.append({**entry, "_score": score})

    matches.sort(key=lambda x: x["_score"], reverse=True)
    # 清理内部字段
    results = [{k: v for k, v in m.items() if k != "_score"} for m in matches]

    if not results:
        out({
            "status": STATUS_WARNING,
            "message": f"未找到匹配 '{args.keyword}' 的规则",
            "data": [],
        }, args.json)
        return

    out({
        "status": STATUS_OK,
        "message": f"找到 {len(results)} 条匹配 '{args.keyword}' 的规则",
        "data": results,
    }, args.json)


def cmd_list(args):
    """sdd list [--type ...] — 列出全部或指定类型的规则。"""
    reg = load_registry()
    entries = reg.get("entries", [])
    if args.type and args.type != "all":
        entries = [e for e in entries if e["type"] == args.type]

    out({
        "status": STATUS_OK,
        "message": f"共 {len(entries)} 条规则" + (f"（类型: {args.type}）" if args.type else ""),
        "data": entries,
    }, args.json)


def cmd_get(args):
    """sdd get <id[@version]> [--summary] [--all-versions] — 读取规则文件。"""
    raw_id = args.id
    pinned_version = None

    # 解析 id@version 格式
    if "@" in raw_id:
        raw_id, pinned_version = raw_id.rsplit("@", 1)

    reg = load_registry()
    entry = next((e for e in reg.get("entries", []) if e["id"] == raw_id), None)

    # --all-versions：列出归档目录中的所有版本
    if args.all_versions:
        ver_dir = VERSIONS_DIR / raw_id
        versions = []
        if ver_dir.exists():
            for vfile in sorted(ver_dir.glob("*.md")):
                vname = vfile.stem
                content = vfile.read_text(encoding="utf-8")
                fm = _extract_frontmatter(content)
                versions.append({
                    "version": vname,
                    "path": str(vfile.relative_to(ROOT)),
                    "title": _extract_title(content, vfile),
                    "created": fm.get("created", ""),
                })
        # 追加当前版本
        if entry:
            versions.append({
                "version": entry.get("version", "current"),
                "path": entry["path"],
                "title": entry["title"],
                "created": entry.get("last_updated", ""),
                "current": True,
            })
        if not versions:
            error_out(f"未找到规则 '{raw_id}' 的任何版本", args.json)
        out({
            "status": STATUS_OK,
            "message": f"{raw_id} 共 {len(versions)} 个版本",
            "data": versions,
        }, args.json)
        return

    # 读取指定版本
    if pinned_version:
        ver_file = VERSIONS_DIR / raw_id / f"{pinned_version}.md"
        if not ver_file.exists():
            error_out(f"未找到 {raw_id}@{pinned_version}，请用 --all-versions 查看可用版本", args.json)
        content = ver_file.read_text(encoding="utf-8")
        fpath = ver_file
    else:
        if not entry:
            error_out(f"未找到规则 '{raw_id}'，请先运行 sdd index 或检查 id 是否正确", args.json)
        fpath = ROOT / entry["path"]
        if not fpath.exists():
            error_out(f"规则文件不存在: {entry['path']}", args.json, code=2)
        content = fpath.read_text(encoding="utf-8")

    # --summary：只返回前 30 行
    if args.summary:
        summary_lines = [l for l in content.splitlines() if l.strip()][:30]
        text = "\n".join(summary_lines)
    else:
        text = content

    fm = _extract_frontmatter(content)
    result = {
        "id": raw_id,
        "version": pinned_version or fm.get("version", entry.get("version", "") if entry else ""),
        "path": str(fpath.relative_to(ROOT)),
        "title": _extract_title(content, fpath),
        "content": text,
        "annotations": _load_annotations(raw_id),
    }
    out({
        "status": STATUS_OK,
        "message": f"规则: {raw_id}" + (f" @{pinned_version}" if pinned_version else ""),
        "data": result,
    }, args.json)


def _load_annotations(rule_id: str) -> list:
    """从规则文件末尾的 ## 用户标注 区加载所有 annotation。"""
    reg = load_registry()
    entry = next((e for e in reg.get("entries", []) if e["id"] == rule_id), None)
    if not entry:
        return []
    fpath = ROOT / entry["path"]
    if not fpath.exists():
        return []
    content = fpath.read_text(encoding="utf-8")
    annotations = []
    in_section = False
    for line in content.splitlines():
        if line.strip() == "## 用户标注":
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            # 解析格式：`- [2026-03-31 12:00] annotation text`
            m = re.match(r"^-\s+\[(.+?)\]\s+(.+)$", line.strip())
            if m:
                annotations.append({"timestamp": m.group(1), "text": m.group(2)})
    return annotations


def cmd_annotate(args):
    """sdd annotate <id> "<text>" — 在规则文件追加持久化标注。"""
    rule_id = args.id
    text = args.text

    # 候选文件（id 以 _CAND_ 包含的情况）
    cand_dir = ROOT / "memory" / "candidates"
    cand_pattern = f"*{rule_id}*.yaml"
    cand_files = list(cand_dir.glob(cand_pattern)) if cand_dir.exists() else []

    if cand_files:
        # 标注候选文件
        fpath = cand_files[0]
        content = fpath.read_text(encoding="utf-8")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        addition = f"\n# annotation [{timestamp}]\n# {text}\n"
        # 追加到 observed_evidence 块后面
        if "observed_evidence:" in content:
            # 在 observed_evidence 块末尾插入
            content = content.rstrip("\n") + addition
        else:
            content += addition
        fpath.write_text(content, encoding="utf-8")
        out({
            "status": STATUS_OK,
            "message": f"已标注候选 {rule_id}: {fpath.name}",
            "data": {"id": rule_id, "file": str(fpath.relative_to(ROOT)), "annotation": text},
        }, args.json)
        return

    # 普通规则文件
    reg = load_registry()
    entry = next((e for e in reg.get("entries", []) if e["id"] == rule_id), None)
    if not entry:
        error_out(f"未找到规则或候选 '{rule_id}'", args.json)

    fpath = ROOT / entry["path"]
    if not fpath.exists():
        error_out(f"规则文件不存在: {entry['path']}", args.json, code=2)

    content = fpath.read_text(encoding="utf-8")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    annotation_line = f"- [{timestamp}] {text}"

    # 找到或创建 ## 用户标注 区
    if "## 用户标注" in content:
        # 在最后一条 annotation 后插入
        lines = content.rstrip("\n").split("\n")
        insert_idx = len(lines)
        # 找到 ## 用户标注 后的位置
        in_section = False
        last_ann_idx = -1
        for i, line in enumerate(lines):
            if line.strip() == "## 用户标注":
                in_section = True
                last_ann_idx = i
                continue
            if in_section:
                if line.startswith("## "):
                    insert_idx = i
                    break
                if line.strip():
                    last_ann_idx = i
        insert_idx = last_ann_idx + 1
        lines.insert(insert_idx, annotation_line)
        new_content = "\n".join(lines) + "\n"
    else:
        new_content = content.rstrip("\n") + f"\n\n## 用户标注\n\n{annotation_line}\n"

    fpath.write_text(new_content, encoding="utf-8")
    # 刷新注册表
    _refresh_registry_entry(entry, fpath)

    out({
        "status": STATUS_OK,
        "message": f"已标注规则 {rule_id}",
        "data": {
            "id": rule_id,
            "file": entry["path"],
            "annotation": text,
            "timestamp": timestamp,
        },
    }, args.json)


def _refresh_registry_entry(entry: dict, fpath: Path):
    """更新单条注册表记录的 last_updated 字段。"""
    if not REGISTRY_PATH.exists():
        return
    try:
        reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        for e in reg.get("entries", []):
            if e["id"] == entry["id"]:
                e["last_updated"] = datetime.now().strftime("%Y-%m-%d")
                break
        REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2))
    except Exception:
        pass  # 注册表刷新失败不阻断主流程


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="sdd",
        description="DEV SDD Framework — Agent-First 规则检索与标注 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  让 Agent 能通过工具调用按语义查找框架规则，而不是依赖 CLAUDE.md 中的硬编码路径。

示例:
  sdd search asyncio              # 搜索与 asyncio 相关的规则
  sdd get tdd-cycle               # 获取 tdd-cycle 规则全文
  sdd get network-guard --summary # 获取摘要（前30行）
  sdd get tdd-cycle@1.0.0         # 获取历史版本
  sdd get tdd-cycle --all-versions  # 列出所有版本
  sdd list --type hook            # 列出所有 hook
  sdd annotate network-guard "asyncio 代码也需要触发此 hook"
  sdd index                       # 重新扫描并更新注册表
""",
    )
    parser.add_argument("--json", action="store_true", help="输出机器友好的 JSON（供 Agent 工具调用解析）")

    subparsers = parser.add_subparsers(dest="cmd", metavar="subcommand")

    # search
    sp = subparsers.add_parser("search", help="按关键词搜索规则")
    sp.add_argument("keyword", help="搜索关键词（支持中文、英文、技术词）")

    # get
    sp = subparsers.add_parser(
        "get",
        help="读取规则文件（支持 id@version 格式）",
        description="读取指定规则的完整内容或摘要。",
        epilog="示例:\n  sdd get tdd-cycle\n  sdd get network-guard --summary\n  sdd get tdd-cycle@1.0.0\n  sdd get tdd-cycle --all-versions",
    )
    sp.add_argument("id", help="规则 id，可附加 @version（如 tdd-cycle@1.0.0）")
    sp.add_argument("--summary", action="store_true", help="只返回前30行摘要")
    sp.add_argument("--all-versions", action="store_true", dest="all_versions",
                    help="列出所有可用历史版本")

    # list
    sp = subparsers.add_parser("list", help="列出全部已注册规则")
    sp.add_argument("--type", default="all",
                    choices=["all", "skill", "hook", "agent", "memory"],
                    help="按类型过滤（默认: all）")

    # annotate
    sp = subparsers.add_parser(
        "annotate",
        help="为规则或候选追加持久化标注",
        description="在规则文件的「用户标注」区追加一条带时间戳的经验记录。",
        epilog='示例:\n  sdd annotate network-guard "asyncio 代码也需要此 hook"\n  sdd annotate HOOK_CAND_XXX_001 "在项目A验证通过"',
    )
    sp.add_argument("id", help="规则 id 或候选 id（如 HOOK_CAND_XXX_001）")
    sp.add_argument("text", help="标注内容（建议说明场景和结论）")

    # index
    sp = subparsers.add_parser("index", help="扫描框架目录，重新生成 memory/registry.json")

    args = parser.parse_args()

    # 把顶层 --json 传递给子命令
    if not hasattr(args, "json") or args.json is None:
        args.json = False

    dispatch = {
        "search": cmd_search,
        "get": cmd_get,
        "list": cmd_list,
        "annotate": cmd_annotate,
        "index": cmd_index,
    }

    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
