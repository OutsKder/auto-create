from __future__ import annotations

import json
import sys
from copy import deepcopy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api_first.pipeline import Pipeline
from backend.api_first.service import (
    approve,
    create_pipeline,
    get_checkpoint,
    get_pipeline,
    list_pipelines,
    reject,
    run_pipeline,
)

DEFAULT_PORT = 8008


def _pipeline_to_dict(pipeline: Pipeline) -> Dict[str, Any]:
    current_stage = pipeline.current_stage()
    checkpoint = pipeline.current_checkpoint()

    if pipeline.status in (pipeline.status.CREATED, pipeline.status.RUNNING):
        next_http = {
            "method": "POST",
            "path": f"/pipelines/{pipeline.id}/run",
            "description": "推进当前阶段并生成 checkpoint",
        }
    elif pipeline.status == pipeline.status.WAITING_APPROVAL and checkpoint:
        next_http = {
            "approve": {
                "method": "POST",
                "path": f"/checkpoints/{checkpoint.id}/approve",
                "description": "审批通过并进入下一阶段",
            },
            "reject": {
                "method": "POST",
                "path": f"/checkpoints/{checkpoint.id}/reject",
                "description": "审批驳回并回到当前阶段待重跑",
            },
        }
    else:
        next_http = None

    return {
        "id": pipeline.id,
        "status": pipeline.status.value,
        "current_stage": {
            "id": current_stage.id,
            "name": current_stage.name,
            "status": current_stage.status.value,
            "meta": current_stage.meta,
        }
        if current_stage
        else None,
        "stages": [
            {
                "id": stage.id,
                "name": stage.name,
                "status": stage.status.value,
                "meta": stage.meta,
            }
            for stage in pipeline.stages
        ],
        "checkpoint": {
            "id": checkpoint.id,
            "stage_id": checkpoint.stage_id,
            "stage_name": checkpoint.stage_name,
            "stage_index": checkpoint.stage_index,
            "status": checkpoint.status.value,
            "note": checkpoint.note,
            "context_snapshot": checkpoint.context_snapshot,
            "meta": checkpoint.meta,
        }
        if checkpoint
        else None,
        "checkpoints": [
            {
                "id": item.id,
                "stage_id": item.stage_id,
                "stage_name": item.stage_name,
                "stage_index": item.stage_index,
                "status": item.status.value,
                "note": item.note,
            }
            for item in pipeline.checkpoints
        ],
        "context": pipeline.context,
        "next_http": next_http,
    }


class PipelineHTTPDemoHandler(BaseHTTPRequestHandler):
    server_version = "ApiFirstDemoHTTP/1.0"

    def _send_json(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        if not raw.strip():
            return {}
        return json.loads(raw)

    def _path_parts(self) -> List[str]:
        return [part for part in urlparse(self.path).path.strip("/").split("/") if part]

    def do_GET(self) -> None:
        parts = self._path_parts()
        try:
            if parts == ["pipelines"]:
                self._send_json(
                    {
                        "total": len(list_pipelines()),
                        "items": [_pipeline_to_dict(item) for item in list_pipelines()],
                    }
                )
                return

            if len(parts) == 2 and parts[0] == "pipelines":
                pipeline = get_pipeline(parts[1])
                self._send_json(_pipeline_to_dict(pipeline))
                return

            if len(parts) == 3 and parts[0] == "pipelines" and parts[2] == "current-stage":
                pipeline = get_pipeline(parts[1])
                current_stage = pipeline.current_stage()
                self._send_json(
                    {
                        "pipeline_id": pipeline.id,
                        "current_stage": None
                        if current_stage is None
                        else {
                            "id": current_stage.id,
                            "name": current_stage.name,
                            "status": current_stage.status.value,
                            "meta": current_stage.meta,
                        },
                    }
                )
                return

            if len(parts) == 2 and parts[0] == "checkpoints":
                checkpoint = get_checkpoint(parts[1])
                self._send_json(
                    {
                        "id": checkpoint.id,
                        "pipeline_id": checkpoint.pipeline_id,
                        "stage_id": checkpoint.stage_id,
                        "stage_name": checkpoint.stage_name,
                        "stage_index": checkpoint.stage_index,
                        "status": checkpoint.status.value,
                        "note": checkpoint.note,
                        "context_snapshot": checkpoint.context_snapshot,
                    }
                )
                return

            self._send_json({"detail": "not found"}, status=HTTPStatus.NOT_FOUND)
        except KeyError:
            self._send_json({"detail": "not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_json({"detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        parts = self._path_parts()
        try:
            if parts == ["pipelines"]:
                payload = self._read_json()
                context = deepcopy(payload.get("context") or {})
                requirement_raw = payload.get("requirement_raw", "")
                if requirement_raw:
                    context["requirement_raw"] = requirement_raw
                if payload.get("demo_mode", True):
                    context["demo_mode"] = True
                pipeline = create_pipeline(context=context)
                self._send_json(_pipeline_to_dict(pipeline), status=HTTPStatus.CREATED)
                return

            if len(parts) == 3 and parts[0] == "pipelines" and parts[2] == "run":
                pipeline = run_pipeline(parts[1])
                self._send_json(_pipeline_to_dict(pipeline))
                return

            if len(parts) == 3 and parts[0] == "checkpoints" and parts[2] in {"approve", "reject"}:
                payload = self._read_json()
                note = (payload.get("note") or "") if isinstance(payload, dict) else ""
                checkpoint = get_checkpoint(parts[1])
                if parts[2] == "approve":
                    pipeline = approve(checkpoint.pipeline_id, checkpoint_id=checkpoint.id)
                else:
                    pipeline = reject(checkpoint.pipeline_id, checkpoint_id=checkpoint.id, note=note)
                self._send_json(_pipeline_to_dict(pipeline))
                return

            self._send_json({"detail": "not found"}, status=HTTPStatus.NOT_FOUND)
        except KeyError:
            self._send_json({"detail": "not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_json({"detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main(port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), PipelineHTTPDemoHandler)
    print(f"API first demo server listening on http://127.0.0.1:{port}")
    print("Endpoints: POST /pipelines, POST /pipelines/{id}/run, POST /checkpoints/{id}/approve, POST /checkpoints/{id}/reject")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
