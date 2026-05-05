from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict

BASE_URL = "http://127.0.0.1:8008"


def request(method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def show(title: str, payload: Dict[str, Any]) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    print("API First HTTP Demo")

    created = request(
        "POST",
        "/pipelines",
        {
            "requirement_raw": "做一个最小 api-first 流程演示，需要可以逐步审批",
            "demo_mode": True,
            "context": {"project": "api-first-demo"},
        },
    )
    show("1. 创建 Pipeline", created)

    pipeline_id = created["id"]

    while True:
        current = request("GET", f"/pipelines/{pipeline_id}")
        status = current["status"]
        current_stage = current.get("current_stage")
        show(f"当前状态: {status}", current)

        if status == "FINISHED":
            break

        if status in {"CREATED", "RUNNING"}:
            ran = request("POST", f"/pipelines/{pipeline_id}/run")
            show("2. run_pipeline", ran)
            continue

        if status == "WAITING_APPROVAL":
            checkpoint = current.get("checkpoint")
            if not checkpoint:
                raise RuntimeError("waiting approval but no checkpoint found")
            approved = request(
                "POST",
                f"/checkpoints/{checkpoint['id']}/approve",
                {"note": f"approve stage {checkpoint['stage_id']}"},
            )
            show("3. approve", approved)
            continue

        raise RuntimeError(f"unexpected pipeline status: {status}")

    print("\n完成：流程已经走到 FINISHED。")


if __name__ == "__main__":
    main()
