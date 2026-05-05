import os
import sys
import json

# Ensure repo root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.agent.codegen.testing_workflow import TestingWorkflow


def main():
    input_path = os.path.join(os.path.dirname(__file__), "testing_workflow_input.json")
    output_path = os.path.join(
        os.path.dirname(__file__), "testing_workflow_output.json"
    )

    with open(input_path, "r", encoding="utf-8") as f:
        context = json.load(f)

    workflow = TestingWorkflow()
    print("Invoking TestingWorkflow...")
    result = workflow.execute(context)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    sandbox_result = (result.get("tests", {}) or {}).get("sandbox_result", {}) or {}
    print(f"Output written to {output_path}")
    print(
        "sandbox_result:",
        {
            "passed": sandbox_result.get("passed"),
            "exit_code": sandbox_result.get("exit_code"),
            "failure_stage": sandbox_result.get("failure_stage"),
            "failure_type": sandbox_result.get("failure_type"),
        },
    )


if __name__ == "__main__":
    main()
