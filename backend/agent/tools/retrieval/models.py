from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RetrievalRequest:
    """Unified input contract for pluggable retrievers."""

    repo_path: str
    points: List[str]
    top_k: int = 20
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalCandidate:
    """Normalized retrieval output item across retrievers."""

    path: str
    score: float
    evidence: List[str] = field(default_factory=list)
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "score": self.score,
            "evidence": self.evidence,
            "source": self.source,
        }
