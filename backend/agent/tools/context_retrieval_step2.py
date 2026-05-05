import ast
import os
import re
from typing import Any, Dict, List, Set, TypedDict

from .retrieval.config_loader import load_rule_pack
from .retrieval.index_builder import ensure_summary_index
from .retrieval.models import RetrievalRequest
from .retrieval.retrievers.keyword_retriever import KeywordRetriever
from .retrieval.retrievers.rule_retriever import RuleRetriever
from .retrieval.retrievers.semantic_retriever import SemanticRetriever


# RequirementStructured: 上游需求分析阶段的结构化输出。
class RequirementStructured(TypedDict, total=False):
    goal: str
    features: List[str]
    constraints: List[str]
    acceptance_criteria: List[str]


# Step2Input: Step2 检索入口参数。
# 该结构由调用方（如 TechArchitect/ContextTool）传入。
class Step2Input(TypedDict, total=False):
    # 当前检索主查询（一般取 requirement_structured.goal）
    query: str
    # 目标代码库绝对路径
    repo_path: str
    # Step1 生成的 Repo-Map 骨架字符串
    repo_skeleton: str
    # 结构化需求对象，用于生成多维检索点
    requirement_structured: RequirementStructured
    # 最终输出 hot_files 的数量上限
    top_k: int
    # import 邻居扩展跳数（默认 1 hop）
    expand_hops: int
    # 单文件内容最大截断长度，防止上下文爆炸
    max_file_chars: int
    # 规则包名称（默认 default），用于多仓库检索策略切换
    rule_pack_name: str
    # 可选：离线摘要索引根目录，默认使用 repo_path/summary
    index_root: str
    # 是否启用摘要索引优先召回
    use_summary_index: bool


# HotFile: Step2 返回的热点文件对象。
# 包含全量/截断代码内容及命中证据，供后续 LLM 直接使用。
class HotFile(TypedDict):
    # 文件相对路径
    path: str
    # 文件全量内容（超长时会截断）
    content: str
    # 综合召回分数（用于排序/审计）
    score: float
    # 命中证据（keyword/rule/import-neighbor 等）
    evidence: List[str]


# CoveragePoint: 单个需求点的覆盖结果。
class CoveragePoint(TypedDict):
    # 需求点文本
    point: str
    # 命中文件数量
    matched_files: int
    # 覆盖状态（covered/partial/uncovered）
    status: str


# CoverageReport: Step2 的覆盖率评估摘要。
class CoverageReport(TypedDict):
    # 各需求点的覆盖明细
    requirement_points: List[CoveragePoint]
    # 未覆盖需求点列表
    uncovered_points: List[str]
    # 风险等级（low/medium/high）
    risk_level: str


# CodebaseContext: Step2 输出给下游 Agent 的标准上下文对象。
class CodebaseContext(TypedDict):
    # 原始查询
    query: str
    # Step1 生成的全局骨架
    repo_skeleton: str
    # 热点文件（全量代码）
    hot_files: List[HotFile]
    # 关键依赖签名（压缩上下文）
    dependency_signatures: List[str]
    # 覆盖率报告
    coverage_report: CoverageReport


SUPPORTED_EXTENSIONS = (".py", ".js", ".ts", ".jsx", ".tsx")
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    "env",
    ".opencode",
    "summary",
}

_RULE_PACK_CACHE: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
_KEYWORD_RETRIEVER_CACHE: Dict[str, KeywordRetriever] = {}
_RULE_RETRIEVER_CACHE: Dict[str, RuleRetriever] = {}
_SEMANTIC_RETRIEVER_CACHE: Dict[str, "SemanticRetriever"] = {}
_SUMMARY_INDEX_CACHE: Dict[str, Dict[str, Any]] = {}


def _resolve_rule_pack_name(rule_pack_name: str) -> str:
    return (rule_pack_name or "default").strip() or "default"


def _get_rule_pack(rule_pack_name: str) -> Dict[str, Dict[str, List[str]]]:
    name = _resolve_rule_pack_name(rule_pack_name)
    if name not in _RULE_PACK_CACHE:
        _RULE_PACK_CACHE[name] = load_rule_pack(name)
    return _RULE_PACK_CACHE[name]


def _get_keyword_retriever(rule_pack_name: str) -> KeywordRetriever:
    name = _resolve_rule_pack_name(rule_pack_name)
    if name not in _KEYWORD_RETRIEVER_CACHE:
        rule_pack = _get_rule_pack(name)
        _KEYWORD_RETRIEVER_CACHE[name] = KeywordRetriever(
            supported_extensions=SUPPORTED_EXTENSIONS,
            skip_dirs=SKIP_DIRS,
            synonym_map=rule_pack.get("synonym_map", {}),
            zh_map=rule_pack.get("zh_map", {}),
        )
    return _KEYWORD_RETRIEVER_CACHE[name]


def _get_rule_retriever(rule_pack_name: str) -> RuleRetriever:
    name = _resolve_rule_pack_name(rule_pack_name)
    if name not in _RULE_RETRIEVER_CACHE:
        rule_pack = _get_rule_pack(name)
        _RULE_RETRIEVER_CACHE[name] = RuleRetriever(
            supported_extensions=SUPPORTED_EXTENSIONS,
            skip_dirs=SKIP_DIRS,
            term_map=rule_pack.get("term_map", {}),
        )
    return _RULE_RETRIEVER_CACHE[name]


def _get_semantic_retriever(rule_pack_name: str):
    # Semantic retriever currently does not require rule pack,
    # but we cache by name to keep symmetric behavior for future options.
    name = _resolve_rule_pack_name(rule_pack_name)
    if name not in _SEMANTIC_RETRIEVER_CACHE:
        _SEMANTIC_RETRIEVER_CACHE[name] = SemanticRetriever(
            supported_extensions=SUPPORTED_EXTENSIONS,
            skip_dirs=SKIP_DIRS,
            term_map=_get_rule_pack(name).get("term_map", {}),
        )
    return _SEMANTIC_RETRIEVER_CACHE[name]


def _summary_index_cache_key(repo_path: str, index_root: str = "") -> str:
    return f"{os.path.abspath(repo_path)}::{os.path.abspath(index_root) if index_root else ''}"


def _get_summary_index(
    repo_path: str,
    index_root: str = "",
    query_points: List[str] | None = None,
    repo_skeleton: str = "",
) -> Dict[str, Any]:
    key = _summary_index_cache_key(repo_path, index_root)
    if key not in _SUMMARY_INDEX_CACHE:
        _SUMMARY_INDEX_CACHE[key] = ensure_summary_index(
            repo_path,
            index_root=index_root or None,
            query_points=query_points or [],
            repo_skeleton=repo_skeleton,
        )
    return _SUMMARY_INDEX_CACHE[key]


def retrieve_precise_context(step2_input: Step2Input) -> CodebaseContext:
    """Step2 主入口：对需求相关代码进行精准召回并返回结构化上下文。"""
    query = step2_input.get("query", "")
    repo_path = step2_input.get("repo_path", "")
    repo_skeleton = step2_input.get("repo_skeleton", "")
    requirement_structured = step2_input.get("requirement_structured", {})
    top_k = int(step2_input.get("top_k", 20))
    # 全局上下文预算（单位：tokens），可由调用方传入以便在大仓中动态控制召回量
    context_budget_tokens = int(step2_input.get("context_budget_tokens", 80000))
    expand_hops = step2_input.get("expand_hops", 1)
    max_file_chars = step2_input.get("max_file_chars", 30000)
    rule_pack_name = _resolve_rule_pack_name(
        step2_input.get("rule_pack_name", "default")
    )
    index_root = step2_input.get("index_root", "") or ""
    use_summary_index = bool(step2_input.get("use_summary_index", True))
    retriever_config = step2_input.get("retriever_config", {}) or {}
    enable_semantic = bool(retriever_config.get("enable_semantic", False))

    try:
        # 输入路径异常时直接降级，返回可解释的空结果结构。
        if not repo_path or not os.path.exists(repo_path):
            points = build_query_points(requirement_structured, query)
            return _fallback_context(query, repo_skeleton, points)

        # 1) 生成检索点：融合 query + requirement_structured 各字段。
        points = build_query_points(requirement_structured, query)
        print(f"[Step2] recall_start points={len(points)}")

        summary_index = {}
        if use_summary_index:
            summary_index = _get_summary_index(
                repo_path,
                index_root=index_root,
                query_points=points,
                repo_skeleton=repo_skeleton,
            )
            if summary_index:
                print(
                    f"[Step2] summary_index_loaded dirs={summary_index.get('dir_count', 0)} files={summary_index.get('file_count', 0)}"
                )

        # 1.1) 基于预算动态计算 top_k：估算 query/repo_skeleton 占用，并使用样本文件估算单文件 token 大小
        def _est_tokens(text: str) -> int:
            return max(1, len(text) // 4)

        est_query_tokens = _est_tokens(query + "\n" + repo_skeleton)
        # 采样仓内文件以估算单文件 token（fallback to 500 tokens）
        sample_count = 0
        sample_chars = 0
        for p in _iter_code_files(repo_path):
            if sample_count >= 50:
                break
            try:
                c = _read_text_for_retrieval(os.path.join(repo_path, p))
                sample_chars += len(c)
                sample_count += 1
            except Exception:
                continue

        if sample_count > 0:
            avg_chars = sample_chars // sample_count
            avg_file_tokens = max(200, avg_chars // 4)
        else:
            avg_file_tokens = 500

        remaining = max(0, context_budget_tokens - est_query_tokens)
        dynamic_top_k = max(1, min(top_k, remaining // max(1, avg_file_tokens)))
        print(
            f"[Step2] budget_tokens={context_budget_tokens} est_query={est_query_tokens} avg_file_tokens={avg_file_tokens} dynamic_top_k={dynamic_top_k}"
        )

        # 2) 多通道召回：关键词召回 + 规则召回 + 可选语义召回，并做候选去重合并。
        summary_candidates = (
            _summary_index_recall(
                summary_index,
                points,
                top_k=dynamic_top_k,
                rule_pack_name=rule_pack_name,
            )
            if summary_index
            else []
        )
        candidates = keyword_recall(
            repo_path, points, top_k=dynamic_top_k, rule_pack_name=rule_pack_name
        )
        rule_candidates = rule_recall(repo_path, points, rule_pack_name=rule_pack_name)
        merged_list = summary_candidates + candidates + rule_candidates
        if enable_semantic:
            semantic_candidates = semantic_recall(
                repo_path, points, top_k=dynamic_top_k, rule_pack_name=rule_pack_name
            )
            merged_list.extend(semantic_candidates)

        merged_candidates = _merge_candidates(merged_list)
        print(f"[Step2] recall_done candidates={len(merged_candidates)}")

        # 3) 防漏扩展：按 import 关系做邻居扩展（N-hop，默认 1 hop）。
        expanded = expand_import_neighbors(
            repo_path, merged_candidates, hops=expand_hops
        )
        print(f"[Step2] expand_done candidates={len(expanded)}")

        # 4) 重排并采样：按分数排序后读取 top_k 热点文件的全量代码内容。
        ranked = rerank_candidates(expanded)
        hot_files = collect_hot_files(
            repo_path, ranked, max_file_chars=max_file_chars, top_k=dynamic_top_k
        )
        print(f"[Step2] hot_files_done count={len(hot_files)}")

        # 5) 结果压缩：抽取依赖签名并生成覆盖率报告，供下游 Agent 使用。
        dependency_signatures = build_dependency_signatures(hot_files)
        coverage_report = build_coverage_report(
            points, hot_files, rule_pack_name=rule_pack_name
        )
        print(
            f"[Step2] coverage_done uncovered={len(coverage_report.get('uncovered_points', []))}"
        )

        # 6) 覆盖率门禁：若存在未覆盖需求点，先进行一次回补检索。
        uncovered_points = coverage_report.get("uncovered_points", [])
        if uncovered_points:
            print(
                f"[Step2][Gate] uncovered_detected count={len(uncovered_points)} -> start_backfill"
            )
            backfill_candidates = coverage_backfill_recall(
                repo_path=repo_path,
                uncovered_points=uncovered_points,
                existing_hot_files=hot_files,
                limit=max(5, len(uncovered_points) * 3),
                rule_pack_name=rule_pack_name,
            )

            if backfill_candidates:
                backfill_hot_files = collect_hot_files(
                    repo_path,
                    backfill_candidates,
                    max_file_chars=max_file_chars,
                    top_k=len(backfill_candidates),
                )
                hot_files = _merge_hot_files(
                    hot_files, backfill_hot_files, top_k=dynamic_top_k
                )
                dependency_signatures = build_dependency_signatures(hot_files)
                coverage_report = build_coverage_report(
                    points, hot_files, rule_pack_name=rule_pack_name
                )

            print(
                f"[Step2][Gate] backfill_done uncovered={len(coverage_report.get('uncovered_points', []))}"
            )

        return {
            "query": query,
            "repo_skeleton": repo_skeleton,
            "hot_files": hot_files,
            "dependency_signatures": dependency_signatures,
            "coverage_report": coverage_report,
        }
    except Exception as e:
        # 任意阶段异常统一降级，确保上游流程不断裂。
        points = build_query_points(requirement_structured, query)
        print(f"[Step2] fallback_on_error: {e}")
        return _fallback_context(query, repo_skeleton, points)


def build_query_points(
    requirement_structured: RequirementStructured, query: str
) -> List[str]:
    """将 query 与结构化需求合并为检索点列表。"""
    points: List[str] = []

    if query:
        points.append(query)

    goal = requirement_structured.get("goal")
    if goal:
        points.append(goal)

    for key in ["features", "constraints", "acceptance_criteria"]:
        for item in requirement_structured.get(key, []) or []:
            if item:
                points.append(item)

    # 去重并过滤
    seen = set()
    out: List[str] = []
    for p in points:
        clean = p.strip()
        if clean and clean not in seen:
            out.append(clean)
            seen.add(clean)

    if not out and query:
        out = [query]
    return out


def _summary_index_recall(
    summary_index: Dict[str, Any],
    points: List[str],
    top_k: int,
    rule_pack_name: str = "default",
) -> List[Dict[str, Any]]:
    """从离线摘要索引中召回候选文件，优先利用文件摘要和目录摘要。"""
    if not summary_index:
        return []

    files = summary_index.get("files", {}) or {}
    dirs = summary_index.get("dirs", {}) or {}
    terms = _expand_terms(points, rule_pack_name=rule_pack_name)
    candidates: List[Dict[str, Any]] = []

    for path, summary in files.items():
        score = 0.0
        evidence: List[str] = []
        haystacks = [
            path,
            summary.get("purpose", ""),
            " ".join(summary.get("main_symbols", [])),
            " ".join(summary.get("exports", [])),
            " ".join(summary.get("keywords", [])),
            " ".join(summary.get("depends_on", [])),
        ]
        joined = " \n".join(haystacks).lower()
        for term in terms:
            if not term:
                continue
            if term in joined:
                score += 0.8
                evidence.append(f"summary_file:{term}")

        dir_path = os.path.dirname(path).replace("\\", "/") or "."
        dir_summary = dirs.get(dir_path, {})
        if dir_summary:
            dir_blob = " ".join(
                [
                    dir_summary.get("purpose", ""),
                    " ".join(dir_summary.get("key_files", [])),
                    " ".join(dir_summary.get("keywords", [])),
                    " ".join(dir_summary.get("exports", [])),
                ]
            ).lower()
            dir_hits = 0
            for term in terms:
                if term and term in dir_blob:
                    dir_hits += 1
            if dir_hits:
                score += 0.25 * dir_hits
                evidence.append("summary_dir")

        if score > 0:
            candidates.append(
                {
                    "path": path,
                    "score": score + float(summary.get("importance_score", 0.0)) * 0.1,
                    "evidence": _dedup_list(evidence),
                    "source": "summary",
                }
            )

    candidates.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return candidates[: max(top_k, 1)]


def keyword_recall(
    repo_path: str, points: List[str], top_k: int, rule_pack_name: str = "default"
) -> List[Dict[str, Any]]:
    """基于路径和文件内容关键词匹配召回候选文件。"""
    request = RetrievalRequest(repo_path=repo_path, points=points, top_k=top_k)
    retriever = _get_keyword_retriever(rule_pack_name)
    return [candidate.to_dict() for candidate in retriever.retrieve(request)]


def rule_recall(
    repo_path: str, points: List[str], rule_pack_name: str = "default"
) -> List[Dict[str, Any]]:
    """基于领域关键词进行规则召回。"""
    request = RetrievalRequest(repo_path=repo_path, points=points, top_k=20)
    retriever = _get_rule_retriever(rule_pack_name)
    return [candidate.to_dict() for candidate in retriever.retrieve(request)]


def semantic_recall(
    repo_path: str, points: List[str], top_k: int, rule_pack_name: str = "default"
) -> List[Dict[str, Any]]:
    """可选的语义检索通道（文件级）。"""
    request = RetrievalRequest(repo_path=repo_path, points=points, top_k=top_k)
    retriever = _get_semantic_retriever(rule_pack_name)
    return [candidate.to_dict() for candidate in retriever.retrieve(request)]


def expand_import_neighbors(
    repo_path: str, candidates: List[Dict[str, Any]], hops: int
) -> List[Dict[str, Any]]:
    """基于 import 邻居扩展候选文件，默认 1 hop。"""
    if hops <= 0 or not candidates:
        return _merge_candidates(candidates)

    all_paths = list(_iter_code_files(repo_path))
    module_map = _build_module_map(all_paths)

    # 构建 import 图
    import_graph: Dict[str, Set[str]] = {}
    reverse_graph: Dict[str, Set[str]] = {}
    for rel_path in all_paths:
        neighbors = _parse_import_neighbors(repo_path, rel_path, module_map)
        import_graph[rel_path] = neighbors
        for n in neighbors:
            reverse_graph.setdefault(n, set()).add(rel_path)

    merged = _merge_candidates(candidates)
    frontier = {c["path"] for c in merged}
    seen = set(frontier)

    for _ in range(hops):
        new_paths: Set[str] = set()
        for p in list(frontier):
            new_paths.update(import_graph.get(p, set()))
            new_paths.update(reverse_graph.get(p, set()))

        new_paths -= seen
        if not new_paths:
            break

        for p in sorted(new_paths):
            merged.append(
                {
                    "path": p,
                    "score": 0.6,
                    "evidence": ["import-neighbor"],
                }
            )

        seen.update(new_paths)
        frontier = new_paths

    return _merge_candidates(merged)


def rerank_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按分数排序并去重。"""
    merged = _merge_candidates(candidates)
    merged.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return merged


def collect_hot_files(
    repo_path: str, ranked: List[Dict[str, Any]], max_file_chars: int, top_k: int
) -> List[HotFile]:
    """读取候选文件全量代码，形成 hot_files。"""
    hot_files: List[HotFile] = []
    seen_paths: Set[str] = set()

    for item in ranked[:top_k]:
        rel_path = _normalize_repo_rel_path(item.get("path", ""))
        if not rel_path:
            continue

        if rel_path in seen_paths:
            continue

        full_path = os.path.join(repo_path, rel_path.replace("/", os.sep))
        if not os.path.exists(full_path):
            continue

        try:
            content = _read_text_for_retrieval(full_path)
        except Exception:
            continue

        if len(content) > max_file_chars:
            content = content[:max_file_chars] + "\n...[Content Truncated]..."

        hot_files.append(
            {
                "path": rel_path,
                "content": content,
                "score": round(float(item.get("score", 0.0)), 4),
                "evidence": _dedup_list(item.get("evidence", [])),
            }
        )
        seen_paths.add(rel_path)

    return hot_files


def coverage_backfill_recall(
    repo_path: str,
    uncovered_points: List[str],
    existing_hot_files: List[HotFile],
    limit: int,
    rule_pack_name: str = "default",
) -> List[Dict[str, Any]]:
    """覆盖率门禁回补召回：针对未覆盖需求点补充候选文件。"""
    existing_paths = {hf.get("path", "") for hf in existing_hot_files}
    point_terms = _expand_terms(uncovered_points, rule_pack_name=rule_pack_name)
    candidates: List[Dict[str, Any]] = []

    for rel_path in _iter_code_files(repo_path):
        normalized_rel_path = _normalize_repo_rel_path(rel_path)
        if normalized_rel_path in existing_paths:
            continue

        full_path = os.path.join(repo_path, normalized_rel_path.replace("/", os.sep))
        try:
            content = _read_text_for_retrieval(full_path).lower()
        except Exception:
            continue

        path_text = normalized_rel_path.lower()
        matched_terms = [
            t for t in point_terms if t and (t in path_text or t in content)
        ]
        if not matched_terms:
            continue

        candidates.append(
            {
                "path": normalized_rel_path,
                "score": 0.7 + 0.1 * len(matched_terms),
                "evidence": [f"coverage-backfill:{t}" for t in matched_terms[:5]],
            }
        )

    candidates = _merge_candidates(candidates)
    candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return candidates[:limit]


def _merge_hot_files(
    primary: List[HotFile], secondary: List[HotFile], top_k: int
) -> List[HotFile]:
    """合并热点文件并按 score 排序去重，保留 top_k。"""
    merged: Dict[str, HotFile] = {}

    for hf in primary + secondary:
        path = _normalize_repo_rel_path(hf.get("path", ""))
        if not path:
            continue

        if path not in merged:
            merged[path] = hf
        else:
            old = merged[path]
            old["score"] = max(old.get("score", 0.0), hf.get("score", 0.0))
            old["evidence"] = _dedup_list(
                old.get("evidence", []) + hf.get("evidence", [])
            )

    ranked = sorted(merged.values(), key=lambda x: x.get("score", 0.0), reverse=True)
    return ranked[:top_k]


def build_dependency_signatures(hot_files: List[HotFile]) -> List[str]:
    """从热文件中提取简要依赖签名，MVP 优先支持 Python。"""
    signatures: List[str] = []

    for hf in hot_files:
        path = _normalize_repo_rel_path(hf.get("path", ""))
        content = hf.get("content", "")

        if path.endswith(".py"):
            try:
                tree = ast.parse(content)
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        signatures.append(f"{path}: class {node.name}")
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [a.arg for a in node.args.args]
                        signatures.append(f"{path}: def {node.name}({', '.join(args)})")
            except Exception:
                pass
        elif path.endswith((".js", ".ts", ".jsx", ".tsx")):
            classes = re.findall(r"class\s+([A-Za-z0-9_]+)", content)
            funcs = re.findall(r"function\s+([A-Za-z0-9_]+)\s*\(", content)
            for c in classes:
                signatures.append(f"{path}: class {c}")
            for fn in funcs:
                signatures.append(f"{path}: function {fn}()")

    return _dedup_list(signatures)[:200]


def build_coverage_report(
    points: List[str], hot_files: List[HotFile], rule_pack_name: str = "default"
) -> CoverageReport:
    """根据检索点构建覆盖率报告。"""
    if not points:
        return {
            "requirement_points": [],
            "uncovered_points": [],
            "risk_level": "low",
        }

    requirement_points: List[CoveragePoint] = []
    uncovered: List[str] = []

    for point in points:
        terms = _expand_terms([point], rule_pack_name=rule_pack_name)
        matched = 0

        for hf in hot_files:
            path_text = hf["path"].lower()
            content_text = hf["content"].lower()
            if any(t in path_text or t in content_text for t in terms):
                matched += 1

        status = "covered" if matched > 0 else "uncovered"
        if matched == 0:
            uncovered.append(point)

        requirement_points.append(
            {
                "point": point,
                "matched_files": matched,
                "status": status,
            }
        )

    if len(uncovered) == 0:
        risk = "low"
    elif len(uncovered) <= max(1, len(points) // 3):
        risk = "medium"
    else:
        risk = "high"

    return {
        "requirement_points": requirement_points,
        "uncovered_points": uncovered,
        "risk_level": risk,
    }


def _fallback_context(
    query: str, repo_skeleton: str, points: List[str]
) -> CodebaseContext:
    return {
        "query": query,
        "repo_skeleton": repo_skeleton,
        "hot_files": [],
        "dependency_signatures": [],
        "coverage_report": {
            "requirement_points": [
                {"point": p, "matched_files": 0, "status": "uncovered"} for p in points
            ],
            "uncovered_points": points,
            "risk_level": "high",
        },
    }


def _iter_code_files(repo_path: str):
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if file.endswith(SUPPORTED_EXTENSIONS):
                full = os.path.join(root, file)
                yield os.path.relpath(full, repo_path)


def _expand_terms(points: List[str], rule_pack_name: str = "default") -> List[str]:
    terms: List[str] = []
    for point in points:
        if not point:
            continue
        lowered = point.lower()
        terms.append(lowered)

        chunks = re.split(r"[\s,，。;；、:/|()\[\]{}]+", lowered)
        for c in chunks:
            c = c.strip()
            if len(c) >= 2:
                terms.append(c)

    # 同义词扩展（来自可配置规则包，支持多仓库替换）
    rule_pack = _get_rule_pack(rule_pack_name)
    synonym_map = rule_pack.get("synonym_map", {})
    zh_map = rule_pack.get("zh_map", {})
    extra = []
    for t in terms:
        for k, vals in synonym_map.items():
            if k in t:
                extra.extend(vals)
        for k, vals in zh_map.items():
            if k in t:
                extra.extend(vals)

    terms.extend(extra)
    return _dedup_list([t for t in terms if t])


def _merge_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for c in candidates:
        path = _normalize_repo_rel_path(c.get("path", ""))
        if not path:
            continue
        if path not in merged:
            merged[path] = {
                "path": path,
                "score": float(c.get("score", 0.0)),
                "evidence": list(c.get("evidence", [])),
            }
        else:
            merged[path]["score"] += float(c.get("score", 0.0))
            merged[path]["evidence"].extend(c.get("evidence", []))
            merged[path]["evidence"] = _dedup_list(merged[path]["evidence"])

    return list(merged.values())


def _build_module_map(paths: List[str]) -> Dict[str, str]:
    module_map: Dict[str, str] = {}
    for p in paths:
        normalized = p.replace("\\", "/")
        no_ext = normalized.rsplit(".", 1)[0]
        module_map[no_ext] = p
        module_map[os.path.basename(no_ext)] = p
    return module_map


def _parse_import_neighbors(
    repo_path: str, rel_path: str, module_map: Dict[str, str]
) -> Set[str]:
    neighbors: Set[str] = set()
    rel_path = _normalize_repo_rel_path(rel_path)
    full_path = os.path.join(repo_path, rel_path.replace("/", os.sep))

    try:
        content = _read_text_for_retrieval(full_path)
    except Exception:
        return neighbors

    if rel_path.endswith(".py"):
        imports = re.findall(r"^\s*import\s+([A-Za-z0-9_\.]+)", content, flags=re.M)
        from_imports = re.findall(
            r"^\s*from\s+([A-Za-z0-9_\.]+)\s+import\s+", content, flags=re.M
        )
        for module in imports + from_imports:
            key = module.replace(".", "/")
            if key in module_map:
                neighbors.add(module_map[key])
            elif module in module_map:
                neighbors.add(module_map[module])
            else:
                base = module.split(".")[-1]
                if base in module_map:
                    neighbors.add(module_map[base])
    else:
        js_imports = re.findall(
            r"import\s+.*?from\s+[\"']([^\"']+)[\"']", content, flags=re.M
        )
        for imp in js_imports:
            if imp.startswith("."):
                base_dir = os.path.dirname(rel_path)
                target = os.path.normpath(os.path.join(base_dir, imp)).replace(
                    "\\", "/"
                )
                for ext in [".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"]:
                    probe = (target + ext).replace("//", "/")
                    if probe in module_map.values():
                        neighbors.add(probe)

    neighbors.discard(rel_path)
    return neighbors


def _normalize_repo_rel_path(path: str) -> str:
    normalized = (path or "").replace("\\", "/")
    normalized = normalized.lstrip("./")
    return normalized


def _read_text_for_retrieval(full_path: str) -> str:
    """Read text robustly across UTF-8/UTF-16 files and strip null bytes."""
    with open(full_path, "rb") as f:
        raw = f.read()

    if not raw:
        return ""

    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            text = raw.decode(encoding)
            break
        except Exception:
            text = ""
    else:
        text = raw.decode("utf-8", errors="ignore")

    if "\x00" in text:
        text = text.replace("\x00", "")

    return text


def _dedup_list(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out
