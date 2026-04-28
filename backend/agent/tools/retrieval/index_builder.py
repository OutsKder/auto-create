"""Offline summary index builder for Step2.

This module creates a lightweight directory/file summary layer under
``summary`` so Step2 can later prefer precomputed summaries before
falling back to live AST parsing.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, DefaultDict, Dict, List, Optional, Sequence, Set, Tuple


SUPPORTED_INDEX_EXTENSIONS = (
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".html",
    ".css",
)

SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    "env",
    ".opencode",
    ".opencode_index",
    "summary",
}


def build_summary_index(
    repo_path: str,
    index_root: Optional[str] = None,
    supported_extensions: Sequence[str] = SUPPORTED_INDEX_EXTENSIONS,
    skip_dirs: Set[str] = SKIP_DIRS,
) -> Dict[str, Any]:
    """Build directory and file summary artifacts for a repository."""
    repo_path = os.path.abspath(repo_path)
    index_root = os.path.abspath(index_root or os.path.join(repo_path, "summary"))
    dirs_root = os.path.join(index_root, "dirs")
    files_root = os.path.join(index_root, "files")

    os.makedirs(dirs_root, exist_ok=True)
    os.makedirs(files_root, exist_ok=True)

    file_summaries: Dict[str, Dict[str, Any]] = {}
    dir_files: DefaultDict[str, List[str]] = defaultdict(list)
    dir_depends: DefaultDict[str, List[str]] = defaultdict(list)
    dir_children: DefaultDict[str, List[str]] = defaultdict(list)

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel_dir = _normalize_rel_path(os.path.relpath(root, repo_path))
        if rel_dir != ".":
            parent_dir = _normalize_rel_path(os.path.dirname(rel_dir))
            dir_children[parent_dir].append(rel_dir)

        for file_name in files:
            if not file_name.endswith(tuple(supported_extensions)):
                continue

            full_path = os.path.join(root, file_name)
            rel_file = _normalize_rel_path(os.path.relpath(full_path, repo_path))
            summary = _summarize_file(full_path, rel_file)
            file_summaries[rel_file] = summary
            dir_files[rel_dir].append(rel_file)
            dir_depends[rel_dir].extend(summary.get("depends_on", []))
            _write_json(
                os.path.join(files_root, rel_file, "file_summary.json"),
                summary,
            )

    dir_summaries: Dict[str, Dict[str, Any]] = {}
    all_dirs = set(dir_files) | set(dir_children) | {"."}
    for rel_dir in sorted(all_dirs):
        summary = _summarize_dir(
            rel_dir=rel_dir,
            file_summaries=file_summaries,
            dir_files=dir_files.get(rel_dir, []),
            child_dirs=dir_children.get(rel_dir, []),
            dir_depends=dir_depends.get(rel_dir, []),
        )
        dir_summaries[rel_dir] = summary
        out_dir = "__root__" if rel_dir == "." else rel_dir
        _write_json(os.path.join(dirs_root, out_dir, "summary.json"), summary)

    manifest = {
        "repo_path": repo_path,
        "index_root": index_root,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dir_count": len(dir_summaries),
        "file_count": len(file_summaries),
        "dirs": dir_summaries,
        "files": file_summaries,
    }
    _write_json(os.path.join(index_root, "manifest.json"), manifest)
    return manifest


def load_summary_index(
    repo_path: str, index_root: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Load an existing summary index if it exists."""
    repo_path = os.path.abspath(repo_path)
    index_root = os.path.abspath(index_root or os.path.join(repo_path, "summary"))
    manifest_path = os.path.join(index_root, "manifest.json")
    if not os.path.exists(manifest_path):
        return None

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def ensure_summary_index(
    repo_path: str,
    index_root: Optional[str] = None,
    query_points: Optional[Sequence[str]] = None,
    repo_skeleton: str = "",
    prefer_llm: bool = True,
    max_llm_files: int = 96,
    max_llm_chars_per_file: int = 12000,
) -> Dict[str, Any]:
    """Load the summary index if it exists, otherwise build it automatically.

    When `prefer_llm` is enabled, the builder first creates a cheap baseline index
    and then enriches the highest-priority files/directories with LLM-generated
    summaries. This keeps the summary pipeline automatic while preventing large
    repos from blowing the model context.
    """
    existing = load_summary_index(repo_path, index_root=index_root)
    if existing:
        print(
            f"[Step2][SummaryIndex] hit_cache dir_count={existing.get('dir_count', 0)} file_count={existing.get('file_count', 0)}"
        )
        return existing

    if prefer_llm:
        print(
            f"[Step2][SummaryIndex] miss_cache -> build_llm_summary_index repo={os.path.abspath(repo_path)}"
        )
        return build_llm_summary_index(
            repo_path=repo_path,
            index_root=index_root,
            query_points=query_points or [],
            repo_skeleton=repo_skeleton,
            max_llm_files=max_llm_files,
            max_llm_chars_per_file=max_llm_chars_per_file,
        )

    return build_summary_index(repo_path, index_root=index_root)


def build_llm_summary_index(
    repo_path: str,
    index_root: Optional[str] = None,
    query_points: Optional[Sequence[str]] = None,
    repo_skeleton: str = "",
    max_llm_files: int = 96,
    max_llm_chars_per_file: int = 12000,
) -> Dict[str, Any]:
    """Build summary artifacts and enrich selected files/directories with LLM summaries.

    The strategy is:
    1. Build a full heuristic baseline index first.
    2. Score files against query points / repo skeleton and keep only the most relevant ones.
    3. Chunk each selected file to bounded slices and ask the LLM for concise JSON summaries.
    4. Recompute directory summaries from the updated file summaries and persist to disk.
    """
    repo_path = os.path.abspath(repo_path)
    index_root = os.path.abspath(index_root or os.path.join(repo_path, "summary"))

    manifest = build_summary_index(repo_path, index_root=index_root)
    file_summaries: Dict[str, Dict[str, Any]] = dict(manifest.get("files", {}) or {})

    candidates = _select_llm_summary_candidates(
        repo_path=repo_path,
        query_points=list(query_points or []),
        repo_skeleton=repo_skeleton,
        limit=max_llm_files,
    )
    print(
        f"[Step2][SummaryIndex] llm_candidates={len(candidates)} max_chars_per_file={max_llm_chars_per_file}"
    )

    enriched_paths: List[str] = []
    for idx, rel_path in enumerate(candidates, start=1):
        full_path = os.path.join(repo_path, rel_path)
        if not os.path.exists(full_path):
            continue

        content = _read_text(full_path)
        if not content:
            continue

        llm_summary = _summarize_file_with_llm(
            repo_path=repo_path,
            rel_path=rel_path,
            content=content[:max_llm_chars_per_file],
            query_points=list(query_points or []),
            repo_skeleton=repo_skeleton,
            max_chars_per_file=max_llm_chars_per_file,
        )
        if llm_summary:
            file_summaries[rel_path] = llm_summary
            enriched_paths.append(rel_path)

        if idx == 1 or idx % 10 == 0 or idx == len(candidates):
            print(
                f"[Step2][SummaryIndex] llm_progress={idx}/{len(candidates)} enriched={len(enriched_paths)}"
            )

    if enriched_paths:
        manifest = _rewrite_summary_index_artifacts(
            repo_path=repo_path,
            index_root=index_root,
            file_summaries=file_summaries,
            extra_metadata={
                "summary_mode": "llm_enriched",
                "enriched_files": len(enriched_paths),
                "candidate_files": len(candidates),
            },
        )

    print(
        f"[Step2][SummaryIndex] done enriched_files={len(enriched_paths)} total_files={manifest.get('file_count', 0)}"
    )

    return manifest


def _summarize_file(full_path: str, rel_file: str) -> Dict[str, Any]:
    content = _read_text(full_path)
    ext = os.path.splitext(full_path)[1].lower()
    language = _language_from_extension(ext)
    symbols: List[str] = []
    exports: List[str] = []
    depends_on: List[str] = []
    keywords: List[str] = _tokenize_path(rel_file)
    purpose = ""

    if ext == ".py":
        purpose, symbols, exports, depends_on, keywords = _summarize_python_file(
            rel_file, content, keywords
        )
    elif ext in {".js", ".ts", ".jsx", ".tsx"}:
        purpose, symbols, exports, depends_on, keywords = _summarize_js_ts_file(
            rel_file, content, keywords
        )
    else:
        purpose = _summarize_text_file(rel_file, content)
        keywords = _dedup_list(keywords + _extract_headings(content))

    if not purpose:
        purpose = _fallback_purpose(rel_file, symbols, keywords)

    return {
        "path": rel_file,
        "language": language,
        "purpose": purpose,
        "main_symbols": _dedup_list(symbols)[:30],
        "exports": _dedup_list(exports)[:30],
        "keywords": _dedup_list(keywords)[:40],
        "depends_on": _dedup_list(depends_on)[:40],
        "size_bytes": len(content.encode("utf-8", errors="ignore")),
        "importance_score": _score_file(symbols, exports, depends_on, content),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _select_llm_summary_candidates(
    repo_path: str,
    query_points: Sequence[str],
    repo_skeleton: str,
    limit: int,
) -> List[str]:
    """Pick the most relevant files to send to the LLM.

    The selector uses cheap signals only: path tokens, AST top-level symbols,
    and query/repo-skeleton term overlap. This avoids feeding the whole repo to
    the model and keeps the summary generation precise.
    """
    scored: List[Tuple[float, str]] = []
    query_terms = _tokenize_query_text(" ".join(query_points))
    skeleton_terms = _tokenize_query_text(repo_skeleton)

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file_name in files:
            if not file_name.endswith(tuple(SUPPORTED_INDEX_EXTENSIONS)):
                continue

            full_path = os.path.join(root, file_name)
            rel_path = _normalize_rel_path(os.path.relpath(full_path, repo_path))
            score = 0.0

            path_blob = rel_path.lower()
            for term in query_terms:
                if term and term in path_blob:
                    score += 4.0
            for term in skeleton_terms:
                if term and term in path_blob:
                    score += 1.5

            try:
                content = _read_text(full_path)
                if rel_path.endswith(".py"):
                    tree = ast.parse(content[:20000])
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            if node.name.lower() in path_blob:
                                score += 3.0
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name.lower() in path_blob:
                                score += 2.5
                else:
                    keywords = _extract_headings(content)
                    for kw in keywords[:3]:
                        if kw.lower() in path_blob:
                            score += 1.0
            except Exception:
                pass

            if score > 0:
                scored.append((score, rel_path))

    scored.sort(key=lambda item: item[0], reverse=True)
    if scored:
        return [path for _, path in scored[: max(1, limit)]]

    fallback_files: List[str] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file_name in files:
            if not file_name.endswith(tuple(SUPPORTED_INDEX_EXTENSIONS)):
                continue
            fallback_files.append(
                _normalize_rel_path(
                    os.path.relpath(os.path.join(root, file_name), repo_path)
                )
            )
    return fallback_files[: max(1, limit)]


def _summarize_file_with_llm(
    repo_path: str,
    rel_path: str,
    content: str,
    query_points: Sequence[str],
    repo_skeleton: str,
    max_chars_per_file: int,
) -> Dict[str, Any]:
    """Summarize a selected file with LLM chunking and robust fallback."""
    ext = os.path.splitext(rel_path)[1].lower()
    language = _language_from_extension(ext)
    chunks = _chunk_text(content, max_chars=max(2000, max_chars_per_file // 3))
    chunk_summaries: List[Dict[str, Any]] = []

    for idx, chunk in enumerate(chunks[:6]):
        payload = _call_summary_llm(
            system_prompt=(
                "You are a codebase summarizer. Return only JSON with keys: "
                "purpose, main_symbols, exports, keywords, depends_on, notes."
            ),
            user_prompt=_build_file_summary_prompt(
                repo_path=repo_path,
                rel_path=rel_path,
                language=language,
                chunk_index=idx + 1,
                chunk_total=len(chunks),
                query_points=query_points,
                repo_skeleton=repo_skeleton,
                content_chunk=chunk,
            ),
        )
        parsed = _safe_json_from_text(payload)
        if parsed and not parsed.get("error"):
            chunk_summaries.append(parsed)

    if not chunk_summaries:
        # LLM unavailable or output invalid: fall back to the heuristic summary.
        return _summarize_file(
            full_path=os.path.join(repo_path, rel_path), rel_file=rel_path
        )

    merged = _merge_chunk_summaries(rel_path, language, chunk_summaries, content)
    return merged


def _merge_chunk_summaries(
    rel_path: str,
    language: str,
    chunk_summaries: Sequence[Dict[str, Any]],
    content: str,
) -> Dict[str, Any]:
    purpose = ""
    symbols: List[str] = []
    exports: List[str] = []
    keywords: List[str] = []
    depends_on: List[str] = []

    for item in chunk_summaries:
        if not purpose:
            purpose = str(item.get("purpose", "")).strip()
        symbols.extend(_coerce_list(item.get("main_symbols", [])))
        exports.extend(_coerce_list(item.get("exports", [])))
        keywords.extend(_coerce_list(item.get("keywords", [])))
        depends_on.extend(_coerce_list(item.get("depends_on", [])))

    if not purpose:
        purpose = _fallback_purpose(rel_path, symbols, keywords)

    return {
        "path": rel_path,
        "language": language,
        "purpose": purpose,
        "main_symbols": _dedup_list(symbols)[:30],
        "exports": _dedup_list(exports)[:30],
        "keywords": _dedup_list(keywords)[:40],
        "depends_on": _dedup_list(depends_on)[:40],
        "size_bytes": len(content.encode("utf-8", errors="ignore")),
        "importance_score": _score_file(symbols, exports, depends_on, content),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary_mode": "llm",
    }


def _rewrite_summary_index_artifacts(
    repo_path: str,
    index_root: str,
    file_summaries: Dict[str, Dict[str, Any]],
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Rewrite the on-disk summary artifacts from an in-memory file summary map."""
    dirs_root = os.path.join(index_root, "dirs")
    files_root = os.path.join(index_root, "files")

    os.makedirs(dirs_root, exist_ok=True)
    os.makedirs(files_root, exist_ok=True)

    dir_files: DefaultDict[str, List[str]] = defaultdict(list)
    dir_depends: DefaultDict[str, List[str]] = defaultdict(list)
    dir_children: DefaultDict[str, List[str]] = defaultdict(list)

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel_dir = _normalize_rel_path(os.path.relpath(root, repo_path))
        if rel_dir != ".":
            parent_dir = _normalize_rel_path(os.path.dirname(rel_dir))
            dir_children[parent_dir].append(rel_dir)

        for file_name in files:
            if not file_name.endswith(tuple(SUPPORTED_INDEX_EXTENSIONS)):
                continue
            rel_file = _normalize_rel_path(
                os.path.relpath(os.path.join(root, file_name), repo_path)
            )
            if rel_file in file_summaries:
                dir_files[rel_dir].append(rel_file)
                dir_depends[rel_dir].extend(
                    file_summaries[rel_file].get("depends_on", [])
                )

    dir_summaries: Dict[str, Dict[str, Any]] = {}
    all_dirs = set(dir_files) | set(dir_children) | {"."}
    for rel_dir in sorted(all_dirs):
        summary = _summarize_dir(
            rel_dir=rel_dir,
            file_summaries=file_summaries,
            dir_files=dir_files.get(rel_dir, []),
            child_dirs=dir_children.get(rel_dir, []),
            dir_depends=dir_depends.get(rel_dir, []),
        )
        dir_summaries[rel_dir] = summary
        out_dir = "__root__" if rel_dir == "." else rel_dir
        _write_json(os.path.join(dirs_root, out_dir, "summary.json"), summary)

    manifest = {
        "repo_path": repo_path,
        "index_root": index_root,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dir_count": len(dir_summaries),
        "file_count": len(file_summaries),
        "dirs": dir_summaries,
        "files": file_summaries,
    }
    if extra_metadata:
        manifest.update(extra_metadata)

    _write_json(os.path.join(index_root, "manifest.json"), manifest)
    return manifest


def _build_file_summary_prompt(
    repo_path: str,
    rel_path: str,
    language: str,
    chunk_index: int,
    chunk_total: int,
    query_points: Sequence[str],
    repo_skeleton: str,
    content_chunk: str,
) -> str:
    query_text = "\n".join(query_points[:10]) if query_points else "(none)"
    skeleton_excerpt = repo_skeleton[:3000] if repo_skeleton else "(none)"
    return (
        f"Repository root: {repo_path}\n"
        f"File path: {rel_path}\n"
        f"Language: {language}\n"
        f"Chunk: {chunk_index}/{chunk_total}\n\n"
        f"Query points:\n{query_text}\n\n"
        f"Repo skeleton excerpt:\n{skeleton_excerpt}\n\n"
        f"Source chunk:\n{content_chunk}\n\n"
        "Return strict JSON only, with keys:\n"
        '{"purpose":"...","main_symbols":["..."],"exports":["..."],"keywords":["..."],"depends_on":["..."],"notes":["..."]}'
    )


def _call_summary_llm(system_prompt: str, user_prompt: str) -> str:
    """Call the project LLM for summary generation, falling back cleanly on failure."""
    try:
        from backend.doubao_llm import chat_with_doubao

        return chat_with_doubao(user_prompt, system_prompt=system_prompt)
    except KeyboardInterrupt:
        # Keep Step2 resilient in long-running tests: degrade to heuristic summary.
        return '{"error": "interrupted"}'
    except Exception as exc:
        return f'{{"error": "{str(exc)}"}}'


def _safe_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    match = re.search(r"\{.*\}", stripped, flags=re.S)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _chunk_text(text: str, max_chars: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    start = 0
    overlap = max(200, max_chars // 10)
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _tokenize_query_text(text: str) -> List[str]:
    if not text:
        return []
    return _dedup_list(
        [
            token
            for token in re.split(r"[^A-Za-z0-9_\u4e00-\u9fff]+", text.lower())
            if token
        ]
    )


def _coerce_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value] if value.strip() else []
    return []


def _summarize_dir(
    rel_dir: str,
    file_summaries: Dict[str, Dict[str, Any]],
    dir_files: Sequence[str],
    child_dirs: Sequence[str],
    dir_depends: Sequence[str],
) -> Dict[str, Any]:
    dir_name = "repo root" if rel_dir == "." else rel_dir.replace("\\", "/")
    file_records = [
        file_summaries[path] for path in dir_files if path in file_summaries
    ]
    top_files = sorted(
        file_records,
        key=lambda item: item.get("importance_score", 0.0),
        reverse=True,
    )[:5]
    exports: List[str] = []
    key_files: List[str] = []
    keywords: List[str] = []
    for record in top_files:
        key_files.append(record["path"])
        exports.extend(record.get("exports", []))
        keywords.extend(record.get("keywords", []))

    purpose = _infer_dir_purpose(rel_dir, top_files, child_dirs)
    depends_on = _normalize_dir_dependencies(dir_depends)

    return {
        "dir": rel_dir,
        "dir_name": dir_name,
        "purpose": purpose,
        "key_files": key_files,
        "exports": _dedup_list(exports)[:20],
        "depends_on": depends_on[:20],
        "keywords": _dedup_list(keywords)[:30],
        "file_count": len(file_records),
        "child_dir_count": len(child_dirs),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _summarize_python_file(
    rel_file: str, content: str, keywords: List[str]
) -> Tuple[str, List[str], List[str], List[str], List[str]]:
    symbols: List[str] = []
    exports: List[str] = []
    depends_on: List[str] = []
    purpose = ""

    try:
        tree = ast.parse(content)
        module_doc = ast.get_docstring(tree) or ""
        if module_doc:
            purpose = _first_sentence(module_doc)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(f"def {node.name}")
                exports.append(node.name)
            elif isinstance(node, ast.ClassDef):
                symbols.append(f"class {node.name}")
                exports.append(node.name)
                for class_node in node.body:
                    if isinstance(class_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append(f"{node.name}.{class_node.name}")

            if isinstance(node, ast.Import):
                depends_on.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                depends_on.append(module)
                depends_on.extend(alias.name for alias in node.names)
    except Exception:
        pass

    keywords = _dedup_list(keywords + _tokenize_symbols(symbols))
    if not purpose:
        purpose = _fallback_purpose(rel_file, symbols, keywords)

    return purpose, symbols, exports, depends_on, keywords


def _summarize_js_ts_file(
    rel_file: str, content: str, keywords: List[str]
) -> Tuple[str, List[str], List[str], List[str], List[str]]:
    symbols: List[str] = []
    exports: List[str] = []
    depends_on: List[str] = []
    purpose = ""

    classes = re.findall(r"class\s+([A-Za-z0-9_]+)", content)
    funcs = re.findall(
        r"(?:function\s+|const\s+|let\s+|var\s+)([A-Za-z0-9_]+)\s*(?:=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>|\([^)]*\)\s*\{)",
        content,
    )
    imports = re.findall(r"import\s+.*?from\s+[\"']([^\"']+)[\"']", content)
    exports_found = re.findall(
        r"export\s+(?:default\s+)?(?:class\s+|function\s+)?([A-Za-z0-9_]+)", content
    )

    for class_name in classes:
        symbols.append(f"class {class_name}")
        exports.append(class_name)
    for func_name in funcs:
        symbols.append(f"function {func_name}")
        exports.append(func_name)

    depends_on.extend(imports)
    exports.extend(exports_found)
    if symbols:
        purpose = f"{rel_file} exposes {', '.join(symbols[:3])}"

    keywords = _dedup_list(
        keywords + _tokenize_symbols(symbols) + _tokenize_list(imports)
    )
    if not purpose:
        purpose = _fallback_purpose(rel_file, symbols, keywords)

    return purpose, symbols, exports, depends_on, keywords


def _summarize_text_file(rel_file: str, content: str) -> str:
    headings = _extract_headings(content)
    if headings:
        return f"{rel_file} documentation: {headings[0]}"
    return _fallback_purpose(rel_file, [], _tokenize_path(rel_file))


def _infer_dir_purpose(
    rel_dir: str, top_files: Sequence[Dict[str, Any]], child_dirs: Sequence[str]
) -> str:
    if rel_dir == ".":
        return "Repository root index"

    if top_files:
        primary = top_files[0]
        symbols = primary.get("main_symbols", [])
        if symbols:
            return f"Folder centered on {symbols[0]}"
        keywords = primary.get("keywords", [])
        if keywords:
            return f"Folder for {keywords[0]}"

    if child_dirs:
        return f"Container for {len(child_dirs)} subdirectories"

    return f"Directory for {os.path.basename(rel_dir)}"


def _normalize_dir_dependencies(deps: Sequence[str]) -> List[str]:
    normalized: List[str] = []
    for dep in deps:
        dep = dep.strip()
        if not dep:
            continue
        if "/" in dep or "\\" in dep:
            normalized.append(dep.replace("\\", "/").rsplit("/", 1)[0])
        elif "." in dep:
            normalized.append(dep.rsplit(".", 1)[0])
        else:
            normalized.append(dep)
    return _dedup_list(normalized)


def _score_file(
    symbols: Sequence[str],
    exports: Sequence[str],
    depends_on: Sequence[str],
    content: str,
) -> float:
    score = 0.0
    score += len(symbols) * 1.5
    score += len(exports) * 1.0
    score += min(len(depends_on), 20) * 0.15
    if re.search(r"if __name__ == ['\"]__main__['\"]", content):
        score += 2.0
    if len(content) < 200:
        score -= 0.5
    return round(score, 3)


def _fallback_purpose(
    rel_file: str, symbols: Sequence[str], keywords: Sequence[str]
) -> str:
    if symbols:
        return f"Module around {symbols[0]}"
    if keywords:
        return f"Module about {keywords[0]}"
    base = os.path.basename(rel_file)
    return f"File {base}"


def _extract_headings(content: str) -> List[str]:
    headings: List[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(stripped.lstrip("#").strip())
        elif stripped.startswith("<h") and ">" in stripped:
            headings.append(re.sub(r"<[^>]+>", "", stripped).strip())
        if len(headings) >= 5:
            break
    return [heading for heading in headings if heading]


def _tokenize_path(path: str) -> List[str]:
    tokens = re.split(r"[\\/_.\-]+", path.lower())
    return [token for token in tokens if token]


def _tokenize_symbols(symbols: Sequence[str]) -> List[str]:
    tokens: List[str] = []
    for symbol in symbols:
        tokens.extend(re.split(r"[^A-Za-z0-9_]+", symbol.lower()))
    return [token for token in tokens if token]


def _tokenize_list(values: Sequence[str]) -> List[str]:
    tokens: List[str] = []
    for value in values:
        tokens.extend(re.split(r"[^A-Za-z0-9_]+", value.lower()))
    return [token for token in tokens if token]


def _first_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    for separator in ("。", ".", "!", "?", "\n"):
        if separator in text:
            return text.split(separator, 1)[0].strip()
    return text


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _normalize_rel_path(path: str) -> str:
    return path.replace("\\", "/")


def _dedup_list(items: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if not item:
            continue
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _language_from_extension(ext: str) -> str:
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".md": "markdown",
        ".txt": "text",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".html": "html",
        ".css": "css",
    }.get(ext, "text")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Step2 summary index artifacts.")
    parser.add_argument("repo_path", help="Repository root to index")
    parser.add_argument(
        "--index-root",
        default=None,
        help="Where to write the summary index (defaults to <repo>/summary)",
    )
    args = parser.parse_args()

    manifest = build_summary_index(args.repo_path, index_root=args.index_root)
    print(
        json.dumps(
            {
                "repo_path": manifest["repo_path"],
                "index_root": manifest["index_root"],
                "dir_count": manifest["dir_count"],
                "file_count": manifest["file_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
