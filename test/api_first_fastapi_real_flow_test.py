import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = Path(__file__).with_name("api_first_fastapi_real_flow_input.json")
OUTPUT_PATH = Path(__file__).with_name("api_first_fastapi_real_flow_output.json")


def load_input() -> Dict[str, Any]:
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def request_json(
    base_url: str,
    method: str,
    path: str,
    payload: Dict[str, Any] | None = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_until_ready(base_url: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            request_json(base_url, "GET", "/openapi.json")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"FastAPI server did not become ready in time: {last_error}")


def snapshot(step: str, request: Dict[str, Any] | None, response: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "step": step,
        "request": request,
        "response": response,
        "pipeline_status": response.get("status"),
        "current_stage": response.get("current_stage", {}),
        "checkpoint": response.get("checkpoint"),
        "next_http": response.get("next_http"),
        "context_keys": sorted(list((response.get("context") or {}).keys())),
    }


def main() -> None:
    payload = load_input()
    os.environ.setdefault("TEST_LLM_PROVIDER", payload.get("provider", "doubao"))

    host = payload.get("server", {}).get("host", "127.0.0.1")
    port = int(payload.get("server", {}).get("port", 8012))
    base_url = f"http://{host}:{port}"

    server_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.api_first.scheduler_api:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    env = os.environ.copy()
    env.setdefault("TEST_LLM_PROVIDER", payload.get("provider", "doubao"))

    server = subprocess.Popen(
        server_cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    steps: List[Dict[str, Any]] = []
    try:
        wait_until_ready(base_url, int(payload.get("timeouts", {}).get("startup_seconds", 45)))

        request_timeout = int(payload.get("timeouts", {}).get("step_seconds", 300))

        created = request_json(
            base_url,
            "POST",
            "/pipelines",
            {
                "requirement_raw": payload["requirement_raw"],
                "context": {
                    **payload.get("codebase", {}),
                    "codebase": payload.get("codebase", {}),
                    "workflow": "api_first_fastapi_real_flow",
                },
            },
            timeout=request_timeout,
        )
        steps.append(snapshot("create_pipeline", {"method": "POST", "path": "/pipelines"}, created))

        pipeline_id = created["id"]
        approvals = payload.get("approval_notes", {})
        step_seconds = int(payload.get("timeouts", {}).get("step_seconds", 300))

        while True:
            current = request_json(base_url, "GET", f"/pipelines/{pipeline_id}")
            steps.append(snapshot("get_pipeline", {"method": "GET", "path": f"/pipelines/{pipeline_id}"}, current))

            status = current["status"]
            if status == "FINISHED":
                break

            if status in {"CREATED", "RUNNING"}:
                ran = request_json(
                    base_url,
                    "POST",
                    f"/pipelines/{pipeline_id}/run",
                    timeout=request_timeout,
                )
                steps.append(snapshot("run_pipeline", {"method": "POST", "path": f"/pipelines/{pipeline_id}/run"}, ran))
                time.sleep(1)
                continue

            if status == "WAITING_APPROVAL":
                checkpoint = current.get("checkpoint")
                if not checkpoint:
                    raise RuntimeError("pipeline is waiting for approval but checkpoint is missing")

                stage_id = checkpoint["stage_id"]
                approval_note = approvals.get(stage_id, f"approve stage {stage_id}")
                approved = request_json(
                    base_url,
                    "POST",
                    f"/checkpoints/{checkpoint['id']}/approve",
                    {"note": approval_note},
                    timeout=request_timeout,
                )
                steps.append(
                    snapshot(
                        "approve_checkpoint",
                        {
                            "method": "POST",
                            "path": f"/checkpoints/{checkpoint['id']}/approve",
                            "note": approval_note,
                        },
                        approved,
                    )
                )
                time.sleep(1)
                continue

            raise RuntimeError(f"unexpected pipeline status: {status}")

        final_pipeline = request_json(base_url, "GET", f"/pipelines/{pipeline_id}")
        output = {
            "input": payload,
            "success": True,
            "final_pipeline": final_pipeline,
            "timeline": steps,
            "stage_outputs": {
                "analysis_doc": final_pipeline.get("context", {}).get("analysis_doc"),
                "requirement_structured": final_pipeline.get("context", {}).get("requirement_structured"),
                "design_doc": final_pipeline.get("context", {}).get("design_doc"),
                "code_diff": final_pipeline.get("context", {}).get("code_diff"),
                "test_report": final_pipeline.get("context", {}).get("test_report"),
                "review_result": final_pipeline.get("context", {}).get("review_result"),
                "delivery": final_pipeline.get("context", {}).get("delivery"),
            },
        }
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"Output written to {OUTPUT_PATH}")
        print(json.dumps({"pipeline_id": pipeline_id, "final_status": final_pipeline["status"]}, ensure_ascii=False, indent=2))
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()

        if server.stdout:
            tail = server.stdout.read()
            if tail:
                print("\n[FastAPI server output]\n")
                print(tail)


if __name__ == "__main__":
    main()
