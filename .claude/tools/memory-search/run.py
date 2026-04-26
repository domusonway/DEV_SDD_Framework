#!/usr/bin/env python3
from __future__ import annotations

"""Rank framework/project memory entries for a task query.

Keyword search is the default no-cost path. Semantic/hybrid modes use a local
SQLite vector cache and Bailian OpenAI-compatible embeddings when configured.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)

ROOT = workflow_cli_common.find_framework_root(__file__)

MEMORY_PATTERNS = ("*.md", "*.yaml", "*.yml")
EXCLUDED_PARTS = {"sessions"}
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-v4"
DEFAULT_LLM_MODEL = "qwen-flash"
DEFAULT_DIMENSIONS = 1024
DEFAULT_VECTOR_DB = ROOT / ".cache" / "dev_sdd" / "memory_vectors.sqlite"


def load_dotenv() -> None:
    """Load root .env without printing secrets and without overriding env."""
    path = ROOT / ".env"
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def tokenize(text: str) -> list[str]:
    raw = re.findall(r"[A-Za-z0-9_./:-]+|[\u4e00-\u9fff]{2,}", text.lower())
    tokens = []
    for item in raw:
        if len(item) >= 2 and item not in tokens:
            tokens.append(item)
    return tokens


def iter_memory_files(project_root: Path | None) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = [("framework", ROOT / "memory")]
    if project_root is not None:
        roots.append(("project", project_root / "memory"))
    files: list[tuple[str, Path]] = []
    for scope, root in roots:
        if not root.exists():
            continue
        for pattern in MEMORY_PATTERNS:
            for path in root.rglob(pattern):
                rel_parts = set(path.relative_to(root).parts)
                if EXCLUDED_PARTS & rel_parts:
                    continue
                files.append((scope, path))
    return sorted(files, key=lambda item: str(item[1]))


def title_from_content(path: Path, content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped.startswith("title:") or stripped.startswith("proposed_rule:"):
            return stripped.split(":", 1)[1].strip().strip("'\"")
    return path.stem


def score_content(content: str, tokens: list[str]) -> int:
    lower = content.lower()
    score = 0
    for token in tokens:
        count = lower.count(token)
        if count:
            score += min(count, 5) * (3 if len(token) >= 4 else 1)
    return score


def snippet_for(content: str, tokens: list[str]) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    for line in lines:
        lower = line.lower()
        if any(token in lower for token in tokens):
            return line[:240]
    return (lines[0] if lines else "")[:240]


def resolve_project(project: str | None) -> tuple[Path | None, str | None]:
    if project:
        return workflow_cli_common.resolve_target_project(project, ROOT)
    if workflow_cli_common.detect_active_project(ROOT):
        return workflow_cli_common.resolve_target_project(None, ROOT)
    return None, None


def collect_documents(project_root: Path | None) -> list[dict[str, Any]]:
    documents = []
    for scope, path in iter_memory_files(project_root if project_root and project_root.exists() else None):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        title = title_from_content(path, content)
        text = f"{title}\n\n{content[:6000]}"
        documents.append({
            "scope": scope,
            "path": workflow_cli_common.rel_path(path, ROOT),
            "absolute_path": path,
            "title": title,
            "content": content,
            "text": text,
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "mtime_ns": path.stat().st_mtime_ns,
        })
    return documents


def keyword_search(query: str, project_root: Path | None, top_k: int) -> list[dict[str, Any]]:
    tokens = tokenize(query)
    hits = []
    if not tokens:
        return hits
    for doc in collect_documents(project_root):
        score = score_content(doc["content"], tokens)
        if score <= 0:
            continue
        hits.append({
            "scope": doc["scope"],
            "path": doc["path"],
            "score": score,
            "keyword_score": score,
            "semantic_score": None,
            "title": doc["title"],
            "snippet": snippet_for(doc["content"], tokens),
        })
    return sorted(hits, key=lambda item: (-int(item["score"]), item["scope"], item["path"]))[:top_k]


def config_from_env(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv()
    framework_config = workflow_cli_common.load_framework_config(ROOT)
    provider_config = workflow_cli_common.get_config_value(framework_config, "providers.bailian", {}) or {}
    memory_config = workflow_cli_common.get_config_value(framework_config, "models.memory_search", {}) or {}
    configured_dimensions = memory_config.get("embedding_dimensions", DEFAULT_DIMENSIONS)
    dimensions = args.dimensions or int(os.getenv("MEMORY_SEARCH_EMBEDDING_DIMENSIONS") or configured_dimensions or DEFAULT_DIMENSIONS)
    base_url = (args.base_url or os.getenv("DASHSCOPE_API_BASE") or provider_config.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
    api_key_env = args.api_key_env or provider_config.get("api_key_env") or "DASHSCOPE_API_KEY"
    api_key = os.getenv(api_key_env) or ""
    return {
        "provider": args.embedding_provider or memory_config.get("embedding_provider") or "auto",
        "base_url": base_url,
        "api_key_present": bool(api_key),
        "api_key": api_key,
        "api_key_env": api_key_env,
        "embedding_model": args.embedding_model or os.getenv("MEMORY_SEARCH_EMBEDDING_MODEL") or memory_config.get("embedding_model") or DEFAULT_EMBEDDING_MODEL,
        "dimensions": dimensions,
        "llm_model": args.llm_model or os.getenv("MEMORY_SEARCH_LLM_MODEL") or memory_config.get("llm_model") or DEFAULT_LLM_MODEL,
        "vector_db": str((ROOT / args.vector_db).resolve() if args.vector_db and not Path(args.vector_db).is_absolute() else Path(args.vector_db or memory_config.get("vector_db") or DEFAULT_VECTOR_DB).resolve()),
    }


def ensure_vector_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_vectors (
            path TEXT NOT NULL,
            scope TEXT NOT NULL,
            title TEXT NOT NULL,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            content_hash TEXT NOT NULL,
            mtime_ns INTEGER NOT NULL,
            embedding_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(path, model, dimensions)
        )
        """
    )
    return conn


def local_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dimensions
        sign = -1.0 if digest[4] % 2 else 1.0
        vector[idx] += sign * (1.0 + min(len(token), 12) / 12.0)
    return normalize(vector)


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(left * right for left, right in zip(a, b))


def bailian_embeddings(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    if not config["api_key"]:
        raise RuntimeError(f"missing {config['api_key_env']}")
    payload = {
        "model": config["embedding_model"],
        "input": texts,
        "dimensions": config["dimensions"],
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{config['base_url']}/embeddings",
        data=data,
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Bailian embeddings HTTP {exc.code}: {detail}") from exc
    embeddings = [item.get("embedding") for item in sorted(result.get("data", []), key=lambda item: item.get("index", 0))]
    if len(embeddings) != len(texts) or any(not isinstance(item, list) for item in embeddings):
        raise RuntimeError("Bailian embeddings response missing vectors")
    return [normalize([float(value) for value in item]) for item in embeddings]


def embed_texts(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    provider = config["provider"]
    if provider == "local":
        return [local_embedding(text, int(config["dimensions"])) for text in texts]
    if provider in {"auto", "bailian"}:
        return bailian_embeddings(texts, config)
    raise RuntimeError(f"unsupported embedding provider: {provider}")


def cached_document_vectors(documents: list[dict[str, Any]], config: dict[str, Any], rebuild: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    conn = ensure_vector_db(Path(config["vector_db"]))
    stats = {"cached": 0, "embedded": 0, "provider": config["provider"], "warnings": []}
    output = []
    to_embed: list[dict[str, Any]] = []
    model = config["embedding_model"]
    dimensions = int(config["dimensions"])

    for doc in documents:
        row = None
        if not rebuild:
            row = conn.execute(
                "SELECT embedding_json, content_hash, mtime_ns FROM memory_vectors WHERE path=? AND model=? AND dimensions=?",
                (doc["path"], model, dimensions),
            ).fetchone()
        if row and row[1] == doc["content_hash"] and int(row[2]) == int(doc["mtime_ns"]):
            doc = dict(doc)
            doc["embedding"] = [float(value) for value in json.loads(row[0])]
            output.append(doc)
            stats["cached"] += 1
        else:
            to_embed.append(doc)

    for offset in range(0, len(to_embed), 10):
        batch = to_embed[offset:offset + 10]
        vectors = embed_texts([doc["text"] for doc in batch], config)
        for doc, vector in zip(batch, vectors):
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_vectors
                (path, scope, title, model, dimensions, content_hash, mtime_ns, embedding_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc["path"],
                    doc["scope"],
                    doc["title"],
                    model,
                    dimensions,
                    doc["content_hash"],
                    int(doc["mtime_ns"]),
                    json.dumps(vector),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            doc = dict(doc)
            doc["embedding"] = vector
            output.append(doc)
            stats["embedded"] += 1
        conn.commit()
    return output, stats


def semantic_search(query: str, project_root: Path | None, top_k: int, config: dict[str, Any], rebuild: bool, min_score: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    documents = collect_documents(project_root)
    stats = {
        "enabled": True,
        "provider": config["provider"],
        "embedding_model": config["embedding_model"],
        "dimensions": config["dimensions"],
        "llm_model": config["llm_model"],
        "base_url": config["base_url"],
        "api_key_present": config["api_key_present"],
        "vector_db": workflow_cli_common.rel_path(Path(config["vector_db"]), ROOT),
        "warnings": [],
    }
    try:
        docs_with_vectors, cache_stats = cached_document_vectors(documents, config, rebuild=rebuild)
        stats.update(cache_stats)
        query_vector = embed_texts([query], config)[0]
    except Exception as exc:
        stats["enabled"] = False
        stats["warnings"].append(str(exc))
        return [], stats

    hits = []
    tokens = tokenize(query)
    for doc in docs_with_vectors:
        semantic_score = cosine(query_vector, doc["embedding"])
        if semantic_score < min_score:
            continue
        keyword_score = score_content(doc["content"], tokens) if tokens else 0
        hits.append({
            "scope": doc["scope"],
            "path": doc["path"],
            "score": round(semantic_score, 6),
            "keyword_score": keyword_score,
            "semantic_score": round(semantic_score, 6),
            "title": doc["title"],
            "snippet": snippet_for(doc["content"], tokens),
        })
    return sorted(hits, key=lambda item: (-float(item["semantic_score"] or 0.0), -int(item["keyword_score"] or 0), item["path"]))[:top_k], stats


def merge_hybrid(keyword_hits: list[dict[str, Any]], semantic_hits: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    max_keyword = max([float(hit.get("keyword_score") or hit.get("score") or 0) for hit in keyword_hits] or [1.0])
    for rank, hit in enumerate(keyword_hits):
        item = dict(hit)
        keyword_score = float(item.get("keyword_score") or item.get("score") or 0)
        item["keyword_score"] = keyword_score
        item["semantic_score"] = item.get("semantic_score")
        item["score"] = round((keyword_score / max_keyword) * 0.45 + (1.0 / (rank + 1)) * 0.05, 6)
        item["rank_source"] = "keyword"
        merged[item["path"]] = item
    for hit in semantic_hits:
        existing = merged.get(hit["path"])
        semantic_score = float(hit.get("semantic_score") or 0.0)
        keyword_score = float(hit.get("keyword_score") or 0.0)
        hybrid_score = semantic_score * 0.65 + min(keyword_score / max_keyword, 1.0) * 0.35
        if existing:
            existing["semantic_score"] = hit.get("semantic_score")
            existing["keyword_score"] = max(float(existing.get("keyword_score") or 0), keyword_score)
            existing["score"] = round(max(float(existing["score"]), hybrid_score), 6)
            existing["rank_source"] = "hybrid"
        else:
            item = dict(hit)
            item["score"] = round(hybrid_score, 6)
            item["rank_source"] = "semantic"
            merged[item["path"]] = item
    return sorted(merged.values(), key=lambda item: (-float(item["score"]), item["path"]))[:top_k]


def search(query: str, project: str | None = None, top_k: int = 5, mode: str = "keyword", config: dict[str, Any] | None = None, rebuild: bool = False, min_score: float = 0.0) -> dict[str, Any]:
    project_root, project_label = resolve_project(project)
    tokens = tokenize(query)
    if not tokens and mode == "keyword":
        return {"query": query, "tokens": [], "project": project_label, "mode": mode, "hits": []}

    keyword_hits = keyword_search(query, project_root, top_k=top_k if mode == "keyword" else max(top_k * 2, 10))
    semantic_hits: list[dict[str, Any]] = []
    semantic = {"enabled": False, "warnings": []}
    if mode in {"semantic", "hybrid"} and config is not None:
        semantic_hits, semantic = semantic_search(query, project_root, top_k=max(top_k * 2, 10), config=config, rebuild=rebuild, min_score=min_score)

    if mode == "semantic":
        hits = semantic_hits[:top_k] if semantic.get("enabled") else keyword_hits[:top_k]
    elif mode == "hybrid":
        hits = merge_hybrid(keyword_hits, semantic_hits, top_k) if semantic.get("enabled") else keyword_hits[:top_k]
    else:
        hits = keyword_hits[:top_k]

    return {
        "query": query,
        "tokens": tokens,
        "project": project_label,
        "mode": mode,
        "hits": hits,
        "keyword_hits": keyword_hits[:top_k],
        "semantic_hits": semantic_hits[:top_k],
        "semantic": {key: value for key, value in semantic.items() if key != "api_key"},
    }


def record_loaded(project: str | None, task: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    project_root, project_label = workflow_cli_common.resolve_target_project(project, ROOT)
    if project_root is None or not project_root.exists():
        return []
    path = project_root / "memory" / "memory_usage.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    events = []
    for hit in hits:
        event = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "project": project_label,
            "memory_id": hit["path"],
            "source": hit["scope"],
            "task": task,
            "outcome": "loaded",
            "note": f"memory-search score={hit['score']}",
        }
        events.append(event)
    if events:
        with open(path, "a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV_SDD memory search")
    parser.add_argument("query", nargs="*", help="task/query text")
    parser.add_argument("--project", default=None, help="project name/path; defaults to active project")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--mode", choices=["keyword", "semantic", "hybrid"], default="keyword")
    parser.add_argument("--embedding-provider", choices=["auto", "bailian", "local"], default=os.getenv("MEMORY_SEARCH_EMBEDDING_PROVIDER"))
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--dimensions", type=int, default=None)
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--vector-db", default=None)
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--record-loaded", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    query = " ".join(args.query).strip()
    config = config_from_env(args) if args.mode in {"semantic", "hybrid"} else None
    result = search(
        query,
        project=args.project,
        top_k=max(1, args.top_k),
        mode=args.mode,
        config=config,
        rebuild=args.rebuild_index,
        min_score=max(0.0, args.min_score),
    )
    recorded = record_loaded(args.project, query, result["hits"]) if args.record_loaded else []
    result["recorded_events"] = recorded
    if args.json:
        print(json.dumps({"status": "ok", "message": "memory search complete", "data": result}, ensure_ascii=False, indent=2))
    else:
        print(f"memory search complete: {len(result['hits'])} hits ({args.mode})")
        warnings = result.get("semantic", {}).get("warnings") or []
        for warning in warnings:
            print(f"warning: {warning}")
        for hit in result["hits"]:
            print(f"- [{hit['score']}] {hit['path']}: {hit['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
