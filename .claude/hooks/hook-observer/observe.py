#!/usr/bin/env python3
"""
hook-observer/observe.py
分析 session 历史，检测 Hook 触发健康度，生成 Hook 类型改进候选

用法:
  python3 .claude/hooks/hook-observer/observe.py <project_name>
  python3 .claude/hooks/hook-observer/observe.py --all   # 扫描全部项目
"""
import sys
import os
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


def find_framework_root() -> Path:
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return current


ROOT = find_framework_root()
CANDIDATES_DIR = ROOT / "memory" / "candidates"

# ── 触发条件注册表 ────────────────────────────────────────────────────────────
# 每个 Hook 定义其当前触发关键词和可能漏触发的扩展关键词
HOOK_TRIGGER_REGISTRY = {
    "network-guard": {
        "current_keywords": ["recv", "send", "socket", "sendall", "conn.recv", "conn.send"],
        "candidate_keywords": [
            ("asyncio", "asyncio 异步网络代码"),
            ("aiohttp", "aiohttp HTTP 客户端/服务端"),
            ("websockets", "WebSocket 协议"),
            ("httpx", "httpx HTTP 客户端"),
            ("StreamReader", "asyncio.StreamReader 异步流"),
            ("StreamWriter", "asyncio.StreamWriter 异步写入"),
        ],
        "hook_file": ".claude/hooks/network-guard/HOOK.md",
        "check_file": ".claude/hooks/network-guard/check.py",
    },
    "stuck-detector": {
        "current_keywords": ["STUCK", "stuck-detector", "RED > 2", "RED>2"],
        "candidate_keywords": [
            ("循环失败", "循环失败未被 stuck-detector 捕获"),
            ("第4次", "RED 第4次未触发强制停止"),
            ("第5次", "RED 第5次未触发强制停止"),
        ],
        "hook_file": ".claude/hooks/stuck-detector/HOOK.md",
        "check_file": None,
    },
    "context-budget": {
        "current_keywords": ["context-budget", "HANDOFF", "budget"],
        "candidate_keywords": [
            ("context rot", "context 质量下降未被检测"),
            ("重复输出", "模型开始重复输出，context 已退化"),
        ],
        "hook_file": ".claude/hooks/context-budget/HOOK.md",
        "check_file": None,
    },
}


@dataclass
class MissedTrigger:
    hook_name: str
    session_file: str
    matched_keyword: str
    keyword_description: str
    context_snippet: str


@dataclass
class FalseTrigger:
    hook_name: str
    session_file: str
    trigger_found: bool
    no_followup: bool  # 触发了但没有 CHECKPOINT 记录


def load_sessions(project: str) -> List[tuple]:
    """返回 (session_path, content) 列表"""
    sessions_dir = ROOT / "projects" / project / "memory" / "sessions"
    if not sessions_dir.exists():
        return []
    sessions = []
    for f in sorted(sessions_dir.glob("*.md")):
        try:
            content = f.read_text(encoding="utf-8")
            sessions.append((f, content))
        except Exception:
            pass
    return sessions


def extract_code_snippets_from_session(content: str) -> str:
    """
    F4修复：只提取 session 中 CHECKPOINT 块内的代码内容，
    避免把用户提问或讨论文字误判为"写了网络代码"。
    提取策略：
      1. [CHECKPOINT...] ... [/CHECKPOINT] 块内的内容
      2. 代码围栏 ```python ... ``` 中的内容
    两者取并集，若都不存在则返回空字符串（不扫描全文）。
    """
    import re as _re
    parts = []

    # 提取 CHECKPOINT 块
    for m in _re.finditer(r"\[CHECKPOINT[^\]]*\](.*?)\[/CHECKPOINT\]", content, _re.DOTALL):
        parts.append(m.group(1))

    # 提取 ```python 代码块
    for m in _re.finditer(r"```(?:python|py|bash|sh)\n(.*?)```", content, _re.DOTALL):
        parts.append(m.group(1))

    return "\n".join(parts)


def detect_missed_triggers(sessions: List[tuple]) -> List[MissedTrigger]:
    """
    F4修复：只在 CHECKPOINT 块和代码围栏中检测触发关键词，
    避免用户问题中提到关键词（如「asyncio 是什么」）被误判为漏触发。
    """
    missed = []
    for session_path, full_content in sessions:
        # 提取有效的代码相关内容
        code_content = extract_code_snippets_from_session(full_content)
        if not code_content:
            # session 中没有代码块，无法判断漏触发，跳过
            continue

        for hook_name, config in HOOK_TRIGGER_REGISTRY.items():
            # 当前触发关键词：在全文中查（Hook 触发记录不在代码块里）
            current_triggered = any(kw in full_content for kw in config["current_keywords"])
            for ext_kw, ext_desc in config["candidate_keywords"]:
                # 候选关键词：只在代码内容中查
                if ext_kw in code_content and not current_triggered:
                    idx = code_content.find(ext_kw)
                    snippet = code_content[max(0, idx - 80):idx + 80].replace("\n", " ")
                    missed.append(MissedTrigger(
                        hook_name=hook_name,
                        session_file=session_path.name,
                        matched_keyword=ext_kw,
                        keyword_description=ext_desc,
                        context_snippet=snippet.strip(),
                    ))
    return missed


def detect_false_triggers(sessions: List[tuple]) -> List[FalseTrigger]:
    """检测触发了但没有后续有效记录的情况（噪声触发）"""
    false_triggers = []
    for session_path, content in sessions:
        for hook_name, config in HOOK_TRIGGER_REGISTRY.items():
            trigger_found = any(kw in content for kw in config["current_keywords"])
            if trigger_found:
                # 检查触发后是否有 CHECKPOINT 记录
                hook_idx = max(
                    content.find(kw) for kw in config["current_keywords"] if kw in content
                )
                post_content = content[hook_idx:]
                has_followup = "[CHECKPOINT" in post_content or "[/CHECKPOINT]" in post_content
                if not has_followup:
                    false_triggers.append(FalseTrigger(
                        hook_name=hook_name,
                        session_file=session_path.name,
                        trigger_found=True,
                        no_followup=True,
                    ))
    return false_triggers


def load_existing_candidates() -> set:
    """返回已有候选的 (target_file, proposed_keyword) 集合，用于去重"""
    existing = set()
    if not CANDIDATES_DIR.exists():
        return existing
    for f in CANDIDATES_DIR.glob("HOOK_CAND_*.yaml"):
        try:
            content = f.read_text(encoding="utf-8")
            target = re.search(r"target_file:\s*(.+)", content)
            keyword = re.search(r"observed_keyword:\s*(.+)", content)
            if target and keyword:
                existing.add((target.group(1).strip(), keyword.group(1).strip()))
        except Exception:
            pass
    return existing


def next_candidate_seq(project_slug: str) -> int:
    """获取下一个候选序号（基于完整项目 slug）"""
    if not CANDIDATES_DIR.exists():
        return 1
    existing = list(CANDIDATES_DIR.glob(f"HOOK_CAND_{project_slug}_*.yaml"))
    if not existing:
        return 1
    nums = []
    for f in existing:
        m = re.search(r"_(\d+)\.yaml$", f.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 1


def write_candidate(
    project: str,
    hook_name: str,
    missed: MissedTrigger,
    existing_candidates: set,
) -> Optional[Path]:
    """生成候选 YAML 文件，已存在则跳过"""
    config = HOOK_TRIGGER_REGISTRY[hook_name]
    dedup_key = (config["hook_file"], missed.matched_keyword)
    if dedup_key in existing_candidates:
        return None

    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    # A1修复：用完整项目名（sanitized）避免三位缩写碰撞
    project_slug = re.sub(r"[^a-zA-Z0-9]", "-", project).upper()[:20]
    seq = next_candidate_seq(project_slug)
    filename = f"HOOK_CAND_{project_slug}_{seq:03d}.yaml"
    filepath = CANDIDATES_DIR / filename

    # 构建 check.py 的扩展建议
    check_addition = ""
    if missed.hook_name == "network-guard":
        if missed.matched_keyword == "asyncio":
            check_addition = """
  asyncio 额外检查项：
  - [ ] read()/readexactly() 是否在 try/except (asyncio.TimeoutError, ConnectionResetError) 块内
  - [ ] EOF 检测：reader.at_eof() 而非 b'' 判断
  - [ ] writer.drain() 是否 await（防止背压积压）
  - [ ] writer.close() 和 await writer.wait_closed() 在 finally 块中"""
        elif missed.matched_keyword in ("aiohttp", "httpx"):
            check_addition = """
  HTTP 客户端额外检查项：
  - [ ] 连接超时是否设置（timeout 参数）
  - [ ] 响应体是否在 async with 上下文中读取（防止连接泄漏）"""

    proposed_diff = f"""在 HOOK.md "触发时机" 描述中补充：
  触发条件扩展：含以下关键词的代码同样触发 {hook_name}：
    - {missed.matched_keyword}（{missed.keyword_description}）

  在 check.py 中新增检查逻辑：{check_addition if check_addition else "（待人工补充具体检查项）"}"""

    content = f"""id: HOOK_CAND_{project_slug}_{seq:03d}
candidate_type: hook_trigger
source_observer: hook-observer
source_project: {project}
observed_evidence: |
  session 文件：{missed.session_file}
  发现关键词：{missed.matched_keyword}（{missed.keyword_description}）
  上下文：...{missed.context_snippet}...
observed_keyword: {missed.matched_keyword}
failure_count: 1
proposed_rule: "{hook_name} 的触发条件应扩展以覆盖 {missed.matched_keyword} 相关代码"
target_file: {config['hook_file']}
secondary_target: {config['check_file'] or 'N/A'}
proposed_diff: |
  {proposed_diff}
confidence: low
domain: network_code
validated_projects:
  - {project}
status: pending_review
created: {datetime.now().strftime('%Y-%m-%d')}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def run_tool_signals(project: str) -> List[str]:
    """读取 sessions 中由 check_tools.sh 写入的 TOOL_SIGNAL 行"""
    signals = []
    sessions_dir = ROOT / "projects" / project / "memory" / "sessions"
    if not sessions_dir.exists():
        return signals
    for f in sessions_dir.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("TOOL_SIGNAL:"):
                signals.append(line)
    return signals


def main():
    parser = argparse.ArgumentParser(description="Hook Observer — 检测 Hook 触发健康度")
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
        # 从 CLAUDE.md 读取当前项目
        claude_md = ROOT / "CLAUDE.md"
        if claude_md.exists():
            m = re.search(r"^PROJECT:\s*(.+)$", claude_md.read_text(), re.MULTILINE)
            if m:
                projects = [m.group(1).strip()]
    if not projects:
        print("❌ 未指定项目，请提供项目名或使用 --all")
        sys.exit(1)

    total_new = 0
    for project in projects:
        print(f"\n[hook-observer] 扫描项目: {project}")
        sessions = load_sessions(project)
        if not sessions:
            print(f"  ⚠️  无 session 文件，跳过")
            continue

        existing = load_existing_candidates()
        missed = detect_missed_triggers(sessions)
        false_triggers = detect_false_triggers(sessions)

        new_files = []
        for m in missed:
            f = write_candidate(project, m.hook_name, m, existing)
            if f:
                new_files.append(f)
                total_new += 1

        # 打印摘要
        if new_files:
            print(f"  ✅ 新增候选 {len(new_files)} 条：")
            for f in new_files:
                data = f.read_text()
                rule_m = re.search(r'proposed_rule: "(.+)"', data)
                rule = rule_m.group(1) if rule_m else f.stem
                print(f"     {f.name}  →  {rule}")
        else:
            print(f"  ✅ 无新漏触发候选（已有候选或无信号）")

        if false_triggers:
            print(f"  ⚠️  发现疑似误触发 {len(false_triggers)} 处（触发后无 CHECKPOINT 记录）：")
            for ft in false_triggers[:3]:
                print(f"     {ft.hook_name} in {ft.session_file}")

        tool_signals = run_tool_signals(project)
        if tool_signals:
            print(f"  📌 检测到 TOOL_SIGNAL {len(tool_signals)} 条（已由 meta-skill-agent 处理）")

    print(f"\n[hook-observer] 总计新增候选：{total_new} 条")
    print(f"  查看全部候选：python3 .claude/tools/skill-tracker/tracker.py candidates")


if __name__ == "__main__":
    main()
