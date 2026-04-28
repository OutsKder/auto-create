import argparse
import os
import subprocess
import sys
from typing import List


def _run(cmd: List[str], title: str) -> int:
    print("\n" + "=" * 72)
    print(f"[Step2 Gate] {title}")
    print("[Step2 Gate] Command:", " ".join(cmd))
    print("=" * 72)

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"[Step2 Gate] FAILED: {title}")
        return result.returncode

    print(f"[Step2 Gate] PASSED: {title}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Step2 retrieval quality gates.")
    parser.add_argument(
        "--with-eval",
        action="store_true",
        help="Also run Step2 baseline evaluation cases.",
    )
    parser.add_argument(
        "--with-e2e",
        action="store_true",
        help="Also run full end-to-end test_requirement_analyst.py",
    )
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    checks = [
        (
            [
                sys.executable,
                os.path.join("backend", "agent", "test_step2_retrieval_minimal.py"),
            ],
            "Minimal Step2 Retrieval Tests",
        )
    ]

    if args.with_eval:
        checks.append(
            (
                [
                    sys.executable,
                    os.path.join("backend", "agent", "run_step2_eval.py"),
                ],
                "Step2 Baseline Evaluation",
            )
        )

    if args.with_e2e:
        checks.append(
            (
                [
                    sys.executable,
                    os.path.join("backend", "test_requirement_analyst.py"),
                ],
                "End-to-End Requirement Analyst Flow",
            )
        )

    cwd = os.getcwd()
    os.chdir(repo_root)
    try:
        for cmd, title in checks:
            code = _run(cmd, title)
            if code != 0:
                return code
    finally:
        os.chdir(cwd)

    print("\n[Step2 Gate] ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
