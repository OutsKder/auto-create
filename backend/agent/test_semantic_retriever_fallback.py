import os
import sys
import tempfile
import unittest

import numpy as np

# Allow direct script execution: python backend/agent/test_semantic_retriever_fallback.py
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from backend.agent.tools.retrieval.models import RetrievalRequest
from backend.agent.tools.retrieval.retrievers import semantic_retriever as sr


class _FakeEmbedder:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def encode(self, texts, convert_to_numpy=True):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    1.0 if "calc" in lowered or "calculator" in lowered else 0.0,
                    1.0 if "precision" in lowered or "float" in lowered else 0.0,
                    float(len(lowered) % 5 + 1),
                ]
            )
        return np.asarray(vectors, dtype=np.float32)


class _FakeFaissIndex:
    def __init__(self, dim: int):
        self.dim = dim
        self.vectors = None

    def add(self, vectors):
        self.vectors = np.asarray(vectors, dtype=np.float32)

    def search(self, query_vectors, k: int):
        scores = np.dot(query_vectors, self.vectors.T)
        order = np.argsort(-scores, axis=1)
        order = order[:, :k]
        sorted_scores = np.take_along_axis(scores, order, axis=1)
        return sorted_scores, order


class _FakeFaissModule:
    @staticmethod
    def IndexFlatIP(dim: int):
        return _FakeFaissIndex(dim)

    @staticmethod
    def normalize_L2(vectors):
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vectors /= norms

    @staticmethod
    def write_index(index, path):
        import pickle

        with open(path, "wb") as f:
            pickle.dump({"dim": index.dim, "vectors": index.vectors}, f)

    @staticmethod
    def read_index(path):
        import pickle

        with open(path, "rb") as f:
            payload = pickle.load(f)
        index = _FakeFaissIndex(payload["dim"])
        index.vectors = payload["vectors"]
        return index


class _FakeVectorizer:
    def __init__(self, max_features=20000):
        self.max_features = max_features
        self.docs = []
        self.vocabulary_ = {}
        self.idf_ = np.asarray([], dtype=float)

    def fit_transform(self, docs):
        self.docs = list(docs)
        self.vocabulary_ = {
            token: idx
            for idx, token in enumerate(
                sorted({token for doc in self.docs for token in doc.lower().split()})
            )
        }
        self.idf_ = np.asarray([1.0] * len(self.vocabulary_), dtype=float)
        return _FakeSparseMatrix(self.docs)

    def transform(self, docs):
        return _FakeSparseMatrix(list(docs))


class _FakeSparseMatrix:
    def __init__(self, docs):
        self.docs = docs

    @property
    def shape(self):
        return (len(self.docs), 1)


class _FakeNearestNeighbors:
    def __init__(self, n_neighbors=64, metric="cosine"):
        self.n_neighbors = n_neighbors
        self.metric = metric
        self.docs = []

    def fit(self, matrix):
        self.docs = list(matrix.docs)
        return self

    def kneighbors(self, query_matrix, n_neighbors=None):
        query = query_matrix.docs[0].lower()
        query_terms = set(query.split())
        scores = []
        for idx, doc in enumerate(self.docs):
            doc_terms = set(doc.lower().split())
            overlap = len(query_terms & doc_terms)
            scores.append((1.0 - min(overlap, 1.0), idx))
        scores.sort(key=lambda item: item[0])
        limit = n_neighbors or self.n_neighbors
        top = scores[:limit]
        dists = np.asarray([[item[0] for item in top]], dtype=float)
        idxs = np.asarray([[item[1] for item in top]], dtype=int)
        return dists, idxs


class SemanticRetrieverFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_sentence_transformer = sr.SentenceTransformer
        self._orig_faiss = sr.faiss
        self._orig_tfidf = sr.TfidfVectorizer
        self._orig_nn = sr.NearestNeighbors
        self._orig_np = sr.np

    def tearDown(self) -> None:
        sr.SentenceTransformer = self._orig_sentence_transformer
        sr.faiss = self._orig_faiss
        sr.TfidfVectorizer = self._orig_tfidf
        sr.NearestNeighbors = self._orig_nn
        sr.np = self._orig_np

    def _write_file(self, root: str, rel_path: str, content: str) -> None:
        full_path = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_faiss_path_is_preferred_when_vector_backend_is_available(self) -> None:
        sr.SentenceTransformer = _FakeEmbedder
        sr.faiss = _FakeFaissModule
        sr.np = np
        sr.TfidfVectorizer = None
        sr.NearestNeighbors = None

        with tempfile.TemporaryDirectory() as repo:
            self._write_file(repo, "core/calculator.py", "class Calculator: pass\n")
            self._write_file(repo, "core/other.py", "def helper():\n    return 1\n")

            retriever = sr.SemanticRetriever(
                supported_extensions=(".py",),
                skip_dirs=set(),
            )
            results = retriever.retrieve(
                RetrievalRequest(repo_path=repo, points=["calculator"], top_k=3)
            )

            self.assertEqual(retriever._vector_backend, "faiss")
            self.assertGreater(len(results), 0)
            self.assertEqual(results[0].path.replace("\\", "/"), "core/calculator.py")

    def test_sklearn_tfidf_fallback_is_used_when_faiss_is_missing(self) -> None:
        sr.SentenceTransformer = None
        sr.faiss = None
        sr.TfidfVectorizer = _FakeVectorizer
        sr.NearestNeighbors = _FakeNearestNeighbors
        sr.np = np

        with tempfile.TemporaryDirectory() as repo:
            self._write_file(
                repo, "core/calculator.py", "def compute_calc():\n    return 1\n"
            )
            self._write_file(
                repo,
                "core/precision_utils.py",
                "def format_precision():\n    return 2\n",
            )

            retriever = sr.SemanticRetriever(
                supported_extensions=(".py",),
                skip_dirs=set(),
            )
            results = retriever.retrieve(
                RetrievalRequest(repo_path=repo, points=["precision"], top_k=3)
            )

            self.assertEqual(retriever._vector_backend, "sklearn_tfidf")
            self.assertGreater(len(results), 0)
            self.assertTrue(
                any("precision_utils.py" in candidate.path for candidate in results)
            )

    def test_substring_fallback_is_used_when_no_vector_backend_exists(self) -> None:
        sr.SentenceTransformer = None
        sr.faiss = None
        sr.TfidfVectorizer = None
        sr.NearestNeighbors = None
        sr.np = np

        with tempfile.TemporaryDirectory() as repo:
            self._write_file(
                repo, "core/calculator.py", "def compute_calc():\n    return 1\n"
            )
            self._write_file(
                repo,
                "core/precision_utils.py",
                "def format_precision():\n    return 2\n",
            )

            retriever = sr.SemanticRetriever(
                supported_extensions=(".py",),
                skip_dirs=set(),
            )
            results = retriever.retrieve(
                RetrievalRequest(repo_path=repo, points=["precision"], top_k=3)
            )

            self.assertEqual(retriever._vector_backend, "none")
            self.assertGreater(len(results), 0)
            self.assertTrue(
                any("precision_utils.py" in candidate.path for candidate in results)
            )


if __name__ == "__main__":
    unittest.main()
