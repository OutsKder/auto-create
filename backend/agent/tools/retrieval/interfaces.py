from typing import List, Protocol

from .models import RetrievalCandidate, RetrievalRequest


class BaseRetriever(Protocol):
    """Pluggable retriever protocol for Step2 multi-channel recall."""

    def retrieve(self, request: RetrievalRequest) -> List[RetrievalCandidate]: ...
