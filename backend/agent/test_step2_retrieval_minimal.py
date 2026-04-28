import os
import sys
import tempfile
import unittest

# Allow direct script execution: python backend/agent/test_step2_retrieval_minimal.py
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from backend.agent.tools import context_retrieval_step2 as step2
from backend.agent.tools.retrieval.config_loader import load_rule_pack


class Step2RetrievalMinimalTests(unittest.TestCase):
    def setUp(self) -> None:
        # Reset in-memory caches to keep each test isolated and deterministic.
        step2._RULE_PACK_CACHE.clear()
        step2._KEYWORD_RETRIEVER_CACHE.clear()
        step2._RULE_RETRIEVER_CACHE.clear()

    def _write_file(self, root: str, rel_path: str, content: str) -> None:
        full_path = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_unknown_rule_pack_falls_back_to_default_json(self) -> None:
        pack = load_rule_pack("pack-not-exists")
        # This key comes from rule_configs/default.json, so fallback should preserve it.
        self.assertIn("计算器", pack.get("zh_map", {}))

    def test_retrieve_precise_context_custom_pack_keeps_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as repo:
            self._write_file(
                repo,
                "core/calculator.py",
                "from core.operations import add\n\n"
                "def compute(op, a, b):\n"
                "    if op == 'mul':\n"
                "        return a * b\n"
                "    return add(a, b)\n",
            )
            self._write_file(
                repo,
                "core/operations.py",
                "def add(a, b):\n"
                "    return a + b\n"
                "\n"
                "def divide(a, b):\n"
                "    return a / b\n",
            )

            default_ctx = step2.retrieve_precise_context(
                {
                    "query": "计算器 乘法 除法 浮点",
                    "repo_path": repo,
                    "repo_skeleton": "stub",
                    "top_k": 10,
                    "expand_hops": 1,
                    "max_file_chars": 20000,
                    "rule_pack_name": "default",
                }
            )
            custom_ctx = step2.retrieve_precise_context(
                {
                    "query": "计算器 乘法 除法 浮点",
                    "repo_path": repo,
                    "repo_skeleton": "stub",
                    "top_k": 10,
                    "expand_hops": 1,
                    "max_file_chars": 20000,
                    "rule_pack_name": "pack-not-exists",
                }
            )

            self.assertGreater(len(default_ctx.get("hot_files", [])), 0)
            self.assertEqual(
                len(default_ctx.get("hot_files", [])),
                len(custom_ctx.get("hot_files", [])),
            )
            self.assertEqual(
                len(default_ctx.get("coverage_report", {}).get("uncovered_points", [])),
                len(custom_ctx.get("coverage_report", {}).get("uncovered_points", [])),
            )

    def test_coverage_backfill_recall_finds_uncovered_targets(self) -> None:
        with tempfile.TemporaryDirectory() as repo:
            self._write_file(
                repo,
                "core/precision_utils.py",
                "def apply_precision(value):\n" "    return round(value, 6)\n",
            )
            self._write_file(
                repo,
                "core/calculator.py",
                "def compute(a, b):\n" "    return a + b\n",
            )

            candidates = step2.coverage_backfill_recall(
                repo_path=repo,
                uncovered_points=["精度 浮点"],
                existing_hot_files=[
                    {
                        "path": "core/calculator.py",
                        "content": "def compute(a, b): return a + b",
                        "score": 2.0,
                        "evidence": ["seed"],
                    }
                ],
                limit=5,
                rule_pack_name="default",
            )
            candidate_paths = {c["path"].replace("\\", "/") for c in candidates}
            self.assertIn("core/precision_utils.py", candidate_paths)


if __name__ == "__main__":
    unittest.main()
