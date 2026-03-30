#!/usr/bin/env python3
"""
permission-auditor/audit.py
分析 session 历史中的权限阻塞信号，生成 settings.local.json 调整候选

用法:
  python3 .claude/hooks/permission-auditor/audit.py <project_name>
"""
import sys
import re
import json
import argparse
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

# 永久 deny 的操作，不生成 relax 候选
# M2修复：扩展永久 deny 列表，覆盖所有 rm 变体和危险操作
PERMANENT_DENY = {
    "git commit", "git push", "git reset", "git checkout", "git merge", "git rebase",
    "Write(.claude/skills", "Write(.claude/hooks", "Write(CLAUDE.md",
    "Write(memory/INDEX.md", "Write(memory/critical",
    "sudo", "pip install", "npm install",
    "rm -rf", "rm -f", "rm -r", "rmdir",   # 所有删除操作变体
}

def _is_permanent_deny(snippet: str) -> bool:
    """检查片段是否涉及永久 deny 操作（支持前缀匹配）"""
    s = snippet.lower()
    return any(pd.lower() in s for pd in PERMANENT_DENY)

# 权限阻塞的特征词
BLOCK_SIGNALS = [
    "permission denied",
    "not allowed",
    "operation not permitted",
    "cannot write",
    "access denied",
    "bash tool not permitted",
]

# 实际使用中发现的 allow 命令模式
USAGE_PATTERN = re.compile(
    r"(?:Bash|Write|Read)\([^)]+\)", re.IGNORECASE
)


def load_settings() -> dict:
    settings_path = ROOT / ".claude" / "settings.local.json"
    if not settings_path.exists():
        return {}
    try:
        return json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_sessions(project: str) -> list:
    sessions_dir = ROOT / "projects" / project / "memory" / "sessions"
    if not sessions_dir.exists():
        return []
    sessions = []
    for f in sorted(sessions_dir.glob("*.md")):
        try:
            sessions.append((f.name, f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return sessions


def detect_blocked_operations(sessions: list) -> list:
    """检测 session 中出现的权限阻塞信号"""
    blocked = []
    for fname, content in sessions:
        content_lower = content.lower()
        for signal in BLOCK_SIGNALS:
            if signal in content_lower:
                idx = content_lower.find(signal)
                snippet = content[max(0, idx - 120):idx + 120].replace("\n", " ")
                # 排除永久 deny 项目
                if not _is_permanent_deny(snippet):
                    blocked.append({
                        "session": fname,
                        "signal": signal,
                        "snippet": snippet.strip(),
                    })
    return blocked


def detect_overly_broad_allows(sessions: list, settings: dict) -> list:
    """检测 allow 规则中范围超出实际使用的情况"""
    allow_rules = settings.get("permissions", {}).get("allow", [])
    allow_rules = [r for r in allow_rules if not r.startswith("//")]

    # 统计实际使用的命令
    actual_usages = set()
    for _, content in sessions:
        for match in USAGE_PATTERN.finditer(content):
            actual_usages.add(match.group(0))

    broad_findings = []
    for rule in allow_rules:
        if "*" in rule and "projects/${PROJECT}" in rule:
            # 检查是否有更精确的模式覆盖实际使用
            broad_findings.append({
                "rule": rule,
                "suggestion": f"考虑将 {rule} 拆分为更精确的规则",
            })
    return broad_findings


def next_seq(project_slug: str) -> int:
    if not CANDIDATES_DIR.exists():
        return 1
    existing = list(CANDIDATES_DIR.glob(f"PERM_CAND_{project_slug}_*.yaml"))
    nums = [int(m.group(1)) for f in existing if (m := re.search(r"_(\d+)\.yaml$", f.name))]
    return max(nums) + 1 if nums else 1


def write_candidate(project: str, ctype: str, evidence: dict, proposed: str) -> Path:
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    # A1修复：用完整项目 slug 避免三位缩写碰撞
    import re as _re
    slug = _re.sub(r"[^a-zA-Z0-9]", "-", project).upper()[:20]
    seq = next_seq(slug)
    filepath = CANDIDATES_DIR / f"PERM_CAND_{slug}_{seq:03d}.yaml"

    content = f"""id: PERM_CAND_{slug}_{seq:03d}
candidate_type: {ctype}
source_observer: permission-auditor
source_project: {project}
observed_evidence: |
  session 文件：{evidence.get('session', 'N/A')}
  信号：{evidence.get('signal', evidence.get('rule', 'N/A'))}
  上下文：{evidence.get('snippet', evidence.get('suggestion', ''))[:200]}
proposed_rule: "{proposed}"
target_file: .claude/settings.local.json
proposed_diff: |
  {proposed}
  （注意：放宽建议优先考虑从 deny → ask，而非直接 allow）
confidence: {"medium" if ctype == "permission_relax" else "low"}
validated_projects:
  - {project}
status: pending_review
created: {datetime.now().strftime('%Y-%m-%d')}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Permission Auditor")
    parser.add_argument("project", help="项目名称")
    args = parser.parse_args()

    project = args.project
    print(f"\n[permission-auditor] 审计项目: {project}")

    sessions = load_sessions(project)
    if not sessions:
        print("  ⚠️  无 session 文件，跳过")
        return

    settings = load_settings()
    blocked = detect_blocked_operations(sessions)
    broad = detect_overly_broad_allows(sessions, settings)

    new_files = []

    for b in blocked[:3]:  # 每次最多 3 条放宽候选
        f = write_candidate(
            project,
            "permission_relax",
            b,
            f"将阻塞的操作从 deny 移至 ask：{b['snippet'][:60]}",
        )
        new_files.append(f)

    for br in broad[:2]:  # 每次最多 2 条收紧候选
        f = write_candidate(
            project,
            "permission_tighten",
            br,
            f"收紧过宽的 allow 规则：{br['rule']}",
        )
        new_files.append(f)

    if new_files:
        print(f"  ✅ 新增权限候选 {len(new_files)} 条：")
        for f in new_files:
            print(f"     {f.name}")
    else:
        print("  ✅ 未检测到权限问题信号")

    print(f"[permission-auditor] 完成")


if __name__ == "__main__":
    main()
