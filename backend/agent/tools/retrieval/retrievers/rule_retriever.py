from typing import Dict, List, Set, Tuple

from ..models import RetrievalCandidate, RetrievalRequest
from ..utils import iter_code_files


class RuleRetriever:
    """Rule-based retriever using configurable domain term maps."""

    def __init__(
        self,
        supported_extensions: Tuple[str, ...],
        skip_dirs: Set[str],
        term_map: Dict[str, List[str]],
    ):
        self.supported_extensions = supported_extensions
        self.skip_dirs = skip_dirs
        self.term_map = term_map

    def retrieve(self, request: RetrievalRequest) -> List[RetrievalCandidate]:
        expanded_rules: Set[str] = set()
        for point in request.points:
            text = point.lower()
            for key, values in self.term_map.items():
                if key in point or any(v in text for v in values):
                    expanded_rules.update(values)

        if not expanded_rules:
            return []

        candidates: List[RetrievalCandidate] = []
        for rel_path in iter_code_files(
            request.repo_path, self.supported_extensions, self.skip_dirs
        ):
            path_text = rel_path.replace("\\", "/").lower()
            matched = [kw for kw in expanded_rules if kw in path_text]
            if matched:
                candidates.append(
                    RetrievalCandidate(
                        path=rel_path,
                        score=1.0 + 0.3 * len(matched),
                        evidence=[f"rule:{kw}" for kw in sorted(matched)],
                        source="rule",
                    )
                )

        return candidates
