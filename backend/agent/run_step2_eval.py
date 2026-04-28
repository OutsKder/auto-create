import argparse
import json
import os
import statistics
import sys
import time
from typing import Any, Dict, List

# Allow direct script execution from repository root.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from backend.agent.tools.codebase_context import CodebaseContextTool


def _normalize_path(path: str) -> str:
    return (path or "").replace("\\", "/")


def _load_cases(cases_path: str) -> List[Dict[str, Any]]:
    with open(cases_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError("Cases file must be a JSON array.")
    return raw


def _recall_at_k(expected_paths: List[str], retrieved_paths: List[str]) -> float:
    expected = {_normalize_path(p) for p in expected_paths if p}
    if not expected:
        return 1.0
    retrieved = {_normalize_path(p) for p in retrieved_paths if p}
    hits = len(expected & retrieved)
    return hits / len(expected)


def _run_case(case: Dict[str, Any], workspace_root: str) -> Dict[str, Any]:
    repo_rel_path = case.get("repo_rel_path", "")
    repo_path = os.path.abspath(os.path.join(workspace_root, repo_rel_path))

    tool = CodebaseContextTool(repo_path)
    query = case.get("query", "")
    top_k = int(case.get("top_k", 20))
    rule_pack_name = case.get("rule_pack_name", "default")

    start = time.perf_counter()
    context = tool.extract_context(
        context={"codebase": {"repo_path": repo_path}},
        query=query,
        rule_pack_name=rule_pack_name,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    hot_files = context.get("hot_files", [])
    retrieved_paths = [hf.get("path", "") for hf in hot_files[:top_k]]

    expected_paths = case.get("expected_paths", [])
    recall = _recall_at_k(expected_paths, retrieved_paths)

    uncovered_points = context.get("coverage_report", {}).get("uncovered_points", [])
    coverage_pass = len(uncovered_points) == 0

    return {
        "id": case.get("id", "unknown"),
        "description": case.get("description", ""),
        "repo_path": repo_path,
        "query": query,
        "expected_paths": [_normalize_path(p) for p in expected_paths],
        "retrieved_paths": [_normalize_path(p) for p in retrieved_paths],
        "recall_at_k": round(recall, 4),
        "coverage_pass": coverage_pass,
        "uncovered_points": uncovered_points,
        "candidate_count": len(hot_files),
        "latency_ms": round(elapsed_ms, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Step2 baseline evaluation.")
    parser.add_argument(
        "--cases",
        default=os.path.join("backend", "agent", "eval", "step2_baseline_cases.json"),
        help="Path to baseline cases json.",
    )
    parser.add_argument(
        "--report",
        default=os.path.join("backend", "agent", "eval", "step2_eval_report.json"),
        help="Path to write evaluation report json.",
    )
    args = parser.parse_args()

    workspace_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    cases_path = os.path.abspath(os.path.join(workspace_root, args.cases))
    report_path = os.path.abspath(os.path.join(workspace_root, args.report))

    cases = _load_cases(cases_path)
    if not cases:
        print("[Step2 Eval] No cases found.")
        return 1

    results: List[Dict[str, Any]] = []
    for case in cases:
        case_result = _run_case(case, workspace_root)
        results.append(case_result)
        print(
            f"[Step2 Eval] case={case_result['id']} recall@k={case_result['recall_at_k']} "
            f"coverage_pass={case_result['coverage_pass']} latency_ms={case_result['latency_ms']}"
        )

    recalls = [r["recall_at_k"] for r in results]
    coverage_pass_rate = sum(1 for r in results if r["coverage_pass"]) / len(results)
    avg_candidates = sum(r["candidate_count"] for r in results) / len(results)
    avg_latency_ms = statistics.mean(r["latency_ms"] for r in results)
    p95_latency_ms = max(r["latency_ms"] for r in results)

    summary = {
        "case_count": len(results),
        "recall_at_k_avg": round(statistics.mean(recalls), 4),
        "recall_at_k_min": round(min(recalls), 4),
        "coverage_pass_rate": round(coverage_pass_rate, 4),
        "avg_candidate_count": round(avg_candidates, 2),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "p95_latency_ms": round(p95_latency_ms, 2),
    }

    report = {
        "summary": summary,
        "results": results,
    }

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("[Step2 Eval] summary:", json.dumps(summary, ensure_ascii=False))
    print(f"[Step2 Eval] report written: {report_path}")

    # Gate rule: baseline quality floor for regression detection.
    if summary["recall_at_k_avg"] < 0.6:
        print("[Step2 Eval] FAILED: recall_at_k_avg below 0.6")
        return 2
    if summary["coverage_pass_rate"] < 0.5:
        print("[Step2 Eval] FAILED: coverage_pass_rate below 0.5")
        return 3

    print("[Step2 Eval] PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
