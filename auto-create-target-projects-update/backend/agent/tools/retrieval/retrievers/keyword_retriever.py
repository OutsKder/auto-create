import os
from typing import Dict, List, Set, Tuple

from ..models import RetrievalCandidate, RetrievalRequest
from ..utils import dedup_list, expand_terms, iter_code_files


class KeywordRetriever:
    """Keyword-based retriever over file paths and file contents."""

    def __init__(
        self,
        supported_extensions: Tuple[str, ...],
        skip_dirs: Set[str],
        synonym_map: Dict[str, List[str]],
        zh_map: Dict[str, List[str]],
    ):
        self.supported_extensions = supported_extensions
        self.skip_dirs = skip_dirs
        self.synonym_map = synonym_map
        self.zh_map = zh_map

    def retrieve(self, request: RetrievalRequest) -> List[RetrievalCandidate]:
        terms = expand_terms(request.points, self.synonym_map, self.zh_map)
        scored: List[RetrievalCandidate] = []

        for rel_path in iter_code_files(
            request.repo_path, self.supported_extensions, self.skip_dirs
        ):
            full_path = os.path.join(request.repo_path, rel_path)

            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            path_text = rel_path.replace("\\", "/").lower()
            body = content.lower()

            score = 0.0
            evidence: List[str] = []
            for term in terms:
                if not term:
                    continue
                in_path = term in path_text
                in_body = term in body
                if in_path:
                    score += 1.2
                    evidence.append(f"keyword_path:{term}")
                if in_body:
                    score += 0.8
                    evidence.append(f"keyword_body:{term}")

            if score > 0:
                scored.append(
                    RetrievalCandidate(
                        path=rel_path,
                        score=score,
                        evidence=dedup_list(evidence),
                        source="keyword",
                    )
                )

        scored.sort(key=lambda x: x.score, reverse=True)
        limit = max(request.top_k * 2, request.top_k)
        return scored[:limit]
