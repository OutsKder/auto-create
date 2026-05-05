import json
import os
import pickle
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
except Exception:  # pragma: no cover - graceful fallback
    np = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import faiss
except Exception:
    faiss = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neighbors import NearestNeighbors
except Exception:
    TfidfVectorizer = None
    NearestNeighbors = None

try:
    from scipy import sparse as scipy_sparse
except Exception:
    scipy_sparse = None

from ..models import RetrievalCandidate, RetrievalRequest
from ..utils import iter_code_files, dedup_list, expand_terms


class SemanticRetriever:
    """Vector-based file-level semantic retriever.

    Behavior:
    - Prefer `sentence-transformers` + `faiss` for embeddings + ANN search.
    - If unavailable, fall back to `sklearn` TF-IDF + NearestNeighbors (cosine).
    - Index is built on first `retrieve` call and cached in memory.
    """

    def __init__(
        self,
        supported_extensions: Tuple[str, ...],
        skip_dirs: set,
        term_map: Dict[str, List[str]] = None,
        embed_model_name: str = "all-MiniLM-L6-v2",
        index_root: Optional[str] = None,
    ):
        self.supported_extensions = supported_extensions
        self.skip_dirs = skip_dirs
        self.term_map = term_map or {}
        self.embed_model_name = embed_model_name
        self.index_root = index_root

        self._file_paths: List[str] = []
        self._docs: List[str] = []
        self._embeddings = None
        self._index = None
        self._vector_backend: Optional[str] = None
        self._vectorizer = None
        self._cached_repo_path: Optional[str] = None

        if SentenceTransformer is not None and faiss is not None and np is not None:
            try:
                self._embedder = SentenceTransformer(self.embed_model_name)
                self._vector_backend = "faiss"
            except Exception:
                self._embedder = None
                self._vector_backend = None
        else:
            self._embedder = None

    def _read_file(self, repo_path: str, rel_path: str) -> str:
        full = os.path.join(repo_path, rel_path)
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def _get_index_dir(self, repo_path: str) -> str:
        base_root = self.index_root or os.path.join(repo_path, "summary")
        return os.path.join(os.path.abspath(base_root), "semantic")

    def _get_cache_paths(self, repo_path: str) -> Dict[str, str]:
        index_dir = self._get_index_dir(repo_path)
        return {
            "index_dir": index_dir,
            "manifest": os.path.join(index_dir, "manifest.json"),
            "docs": os.path.join(index_dir, "docs.json"),
            "file_paths": os.path.join(index_dir, "file_paths.json"),
            "embeddings": os.path.join(index_dir, "embeddings.pkl"),
            "tfidf_vectorizer": os.path.join(index_dir, "tfidf_vectorizer.pkl"),
            "faiss_index": os.path.join(index_dir, "faiss.index"),
        }

    def _persist_state(self, repo_path: str) -> None:
        if self._cached_repo_path != repo_path or not self._file_paths:
            return

        paths = self._get_cache_paths(repo_path)
        os.makedirs(paths["index_dir"], exist_ok=True)

        manifest = {
            "repo_path": os.path.abspath(repo_path),
            "embed_model_name": self.embed_model_name,
            "vector_backend": self._vector_backend,
            "file_count": len(self._file_paths),
        }
        with open(paths["manifest"], "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        with open(paths["docs"], "w", encoding="utf-8") as f:
            json.dump(self._docs, f, ensure_ascii=False)
        with open(paths["file_paths"], "w", encoding="utf-8") as f:
            json.dump(self._file_paths, f, ensure_ascii=False)

        if self._vector_backend == "faiss" and self._index is not None:
            if faiss is not None:
                faiss.write_index(self._index, paths["faiss_index"])
        elif self._vector_backend == "sklearn_tfidf" and self._index is not None:
            if self._embeddings is not None:
                with open(paths["embeddings"], "wb") as f:
                    pickle.dump(self._embeddings, f)
            if self._vectorizer is not None:
                with open(paths["tfidf_vectorizer"], "wb") as f:
                    pickle.dump(self._vectorizer, f)

    def _load_persisted_state(self, repo_path: str) -> bool:
        paths = self._get_cache_paths(repo_path)
        if not os.path.exists(paths["manifest"]):
            return False

        try:
            with open(paths["manifest"], "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            return False

        if manifest.get("repo_path") != os.path.abspath(repo_path):
            return False

        try:
            with open(paths["docs"], "r", encoding="utf-8") as f:
                self._docs = json.load(f)
            with open(paths["file_paths"], "r", encoding="utf-8") as f:
                self._file_paths = json.load(f)
        except Exception:
            return False

        self._vector_backend = manifest.get("vector_backend")
        self._cached_repo_path = os.path.abspath(repo_path)

        if self._vector_backend == "faiss":
            if faiss is None or np is None or self._embedder is None:
                return False
            if not os.path.exists(paths["faiss_index"]):
                return False
            try:
                self._index = faiss.read_index(paths["faiss_index"])
                return True
            except Exception:
                return False

        if self._vector_backend == "sklearn_tfidf":
            if TfidfVectorizer is None or NearestNeighbors is None or np is None:
                return False
            if not os.path.exists(paths["embeddings"]) or not os.path.exists(
                paths["tfidf_vectorizer"]
            ):
                return False
            try:
                with open(paths["tfidf_vectorizer"], "rb") as f:
                    vec = pickle.load(f)
                with open(paths["embeddings"], "rb") as f:
                    X = pickle.load(f)
                nn = NearestNeighbors(n_neighbors=min(64, X.shape[0]), metric="cosine")
                nn.fit(X)
                self._vectorizer = vec
                self._embeddings = X
                self._index = nn
                return True
            except Exception:
                try:
                    with open(paths["docs"], "r", encoding="utf-8") as f:
                        self._docs = json.load(f)
                    vec = TfidfVectorizer(max_features=20000)
                    X = vec.fit_transform(self._docs)
                    nn = NearestNeighbors(
                        n_neighbors=min(64, X.shape[0]), metric="cosine"
                    )
                    nn.fit(X)
                    self._vectorizer = vec
                    self._embeddings = X
                    self._index = nn
                    self._vector_backend = "sklearn_tfidf"
                    self._persist_state(repo_path)
                    return True
                except Exception:
                    return False

        return False

    def _build_index(self, repo_path: str):
        self._file_paths = []
        self._docs = []
        for rel in iter_code_files(
            repo_path, self.supported_extensions, self.skip_dirs
        ):
            txt = self._read_file(repo_path, rel)
            if not txt:
                continue
            self._file_paths.append(rel)
            # limit size to avoid huge embeddings
            self._docs.append(txt[:20000])

        if self._embedder is not None and self._vector_backend == "faiss":
            # use sentence-transformers + faiss
            embs = self._embedder.encode(self._docs, convert_to_numpy=True)
            if embs.dtype != "float32":
                embs = embs.astype("float32")
            dim = embs.shape[1]
            index = faiss.IndexFlatIP(dim)
            faiss.normalize_L2(embs)
            index.add(embs)
            self._embeddings = embs
            self._index = index
            self._vector_backend = "faiss"
        elif TfidfVectorizer is not None and NearestNeighbors is not None:
            # fallback: TF-IDF + sklearn NN (cosine)
            vec = TfidfVectorizer(max_features=20000)
            X = vec.fit_transform(self._docs)
            nn = NearestNeighbors(n_neighbors=min(64, X.shape[0]), metric="cosine")
            nn.fit(X)
            self._vectorizer = vec
            self._index = nn
            self._embeddings = X
            self._vector_backend = "sklearn_tfidf"
        else:
            # last-resort: no vector backend available
            self._vector_backend = "none"

        self._cached_repo_path = os.path.abspath(repo_path)
        self._persist_state(repo_path)

    def retrieve(self, request: RetrievalRequest) -> List[RetrievalCandidate]:
        repo_path = os.path.abspath(request.repo_path)

        if self._cached_repo_path != repo_path:
            self._file_paths = []
            self._docs = []
            self._embeddings = None
            self._index = None
            self._vectorizer = None
            self._cached_repo_path = None

        if not self._file_paths and not self._load_persisted_state(repo_path):
            self._build_index(request.repo_path)

        query_terms = expand_terms(request.points, {}, {})
        query_text = " ".join(query_terms)

        candidates: List[RetrievalCandidate] = []

        if self._vector_backend == "faiss" and self._index is not None:
            q_emb = self._embedder.encode([query_text], convert_to_numpy=True)
            if q_emb.dtype != "float32":
                q_emb = q_emb.astype("float32")
            faiss.normalize_L2(q_emb)
            D, I = self._index.search(
                q_emb, min(request.top_k * 5, len(self._file_paths))
            )
            for score, idx in zip(D[0], I[0]):
                if idx < 0:
                    continue
                path = self._file_paths[int(idx)]
                evidence = [f"semantic:faiss_rank:{int(idx)}"]
                candidates.append(
                    RetrievalCandidate(
                        path=path,
                        score=float(score),
                        evidence=evidence,
                        source="semantic",
                    )
                )
        elif self._vector_backend == "sklearn_tfidf" and self._index is not None:
            qv = self._vectorizer.transform([query_text])
            neigh = min(request.top_k * 5, self._embeddings.shape[0])
            dists, idxs = self._index.kneighbors(qv, n_neighbors=neigh)
            for dist, idx in zip(dists[0], idxs[0]):
                path = self._file_paths[int(idx)]
                score = 1.0 - float(dist)
                evidence = [f"semantic:tfidf_rank:{int(idx)}"]
                candidates.append(
                    RetrievalCandidate(
                        path=path, score=score, evidence=evidence, source="semantic"
                    )
                )
        else:
            # fallback to simple substring match (cheap)
            for rel in self._file_paths:
                txt = self._read_file(request.repo_path, rel)
                s = 0.0
                for t in query_terms:
                    if t and t in txt.lower():
                        s += 1.0
                if s > 0:
                    candidates.append(
                        RetrievalCandidate(
                            path=rel,
                            score=s,
                            evidence=[f"semantic:substr"],
                            source="semantic",
                        )
                    )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[: max(request.top_k * 2, request.top_k)]
