from __future__ import annotations

import json
import logging
import mimetypes
import os
import base64
import re
import sys
import zipfile
from copy import deepcopy
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse

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
DEFAULT_HOST = "127.0.0.1"
LOG_DIR = PROJECT_ROOT / "backend" / "logs"
IMPORTED_PROJECTS_ROOT = PROJECT_ROOT / "projects" / "_imports"
LOGGER = logging.getLogger(__name__)


def _safe_key(value: str, fallback: str = "imported-project") -> str:
    key = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", value.strip(), flags=re.UNICODE).strip(".-")
    return key[:80] or fallback


def _extract_project_zip(filename: str, content_base64: str) -> Dict[str, Any]:
    raw_base64 = content_base64.split(",", 1)[-1]
    archive_bytes = base64.b64decode(raw_base64)
    project_key = _safe_key(Path(filename or "uploaded-project.zip").stem)
    import_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    import_dir = IMPORTED_PROJECTS_ROOT / project_key / import_id
    source_dir = import_dir / "source"
    import_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    zip_path = import_dir / (_safe_key(filename, "uploaded-project.zip"))
    zip_path.write_bytes(archive_bytes)

    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            member_path = source_dir / member.filename
            if not str(member_path.resolve()).startswith(str(source_dir.resolve())):
                raise ValueError(f"zip contains unsafe path: {member.filename}")
        archive.extractall(source_dir)

    files: list[str] = []
    for root, dirs, names in os.walk(source_dir):
        dirs[:] = [item for item in dirs if item not in {"node_modules", ".git", "__pycache__", "venv", ".venv"}]
        for name in names:
            rel_path = Path(root, name).relative_to(source_dir).as_posix()
            files.append(rel_path)
            if len(files) >= 80:
                break
        if len(files) >= 80:
            break

    return {
        "project_key": project_key,
        "import_id": import_id,
        "filename": filename,
        "repo_path": str(source_dir),
        "zip_file": str(zip_path),
        "file_count": sum(len(names) for _, _, names in os.walk(source_dir)),
        "sample_files": files[:20],
    }


def configure_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"server-{datetime.now().strftime('%Y-%m-%d')}.log"
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler],
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    return log_file


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
        "current_stage_index": pipeline.current_stage_index,
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

    def _send_file(
        self,
        path: Path,
        *,
        content_type: str | None = None,
        download_name: str | None = None,
    ) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"detail": "file not found"}, status=HTTPStatus.NOT_FOUND)
            return

        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(body)))
        if download_name:
            safe_name = download_name.encode("ascii", "ignore").decode("ascii") or path.name
            self.send_header(
                "Content-Disposition",
                f"attachment; filename=\"{safe_name}\"; filename*=UTF-8''{quote(download_name)}",
            )
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
        LOGGER.info("GET %s", self.path)
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

            if len(parts) == 3 and parts[0] == "deliveries" and parts[2] in {"download", "preview"}:
                pipeline = get_pipeline(parts[1])
                delivery = pipeline.context.get("delivery") or {}
                package = delivery.get("delivery_package") or pipeline.context.get("delivery_package") or {}
                if not isinstance(package, dict):
                    self._send_json({"detail": "delivery package not ready"}, status=HTTPStatus.NOT_FOUND)
                    return

                if parts[2] == "download":
                    zip_file = Path(str(package.get("zip_file") or ""))
                    self._send_file(
                        zip_file,
                        content_type="application/zip",
                        download_name=zip_file.name,
                    )
                    return

                entry_file = Path(str(package.get("entry_file") or ""))
                self._send_file(entry_file, content_type="text/html; charset=utf-8")
                return

            self._send_json({"detail": "not found"}, status=HTTPStatus.NOT_FOUND)
        except KeyError:
            LOGGER.warning("GET %s not found", self.path)
            self._send_json({"detail": "not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:
            LOGGER.exception("GET %s failed", self.path)
            self._send_json({"detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        parts = self._path_parts()
        LOGGER.info("POST %s", self.path)
        try:
            if parts == ["pipelines"]:
                payload = self._read_json()
                context = deepcopy(payload.get("context") or {})
                requirement_raw = payload.get("requirement_raw", "")
                if requirement_raw:
                    context["requirement_raw"] = requirement_raw
                if payload.get("demo_mode", False):
                    context["demo_mode"] = True
                pipeline = create_pipeline(context=context)
                self._send_json(_pipeline_to_dict(pipeline), status=HTTPStatus.CREATED)
                return

            if parts == ["projects", "import"]:
                payload = self._read_json()
                filename = str(payload.get("filename") or "uploaded-project.zip")
                content_base64 = str(payload.get("content_base64") or "")
                if not content_base64:
                    self._send_json({"detail": "content_base64 is required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if not filename.lower().endswith(".zip"):
                    self._send_json({"detail": "only .zip project archives are supported"}, status=HTTPStatus.BAD_REQUEST)
                    return

                imported = _extract_project_zip(filename, content_base64)
                LOGGER.info(
                    "project.import key=%s import_id=%s files=%s repo=%s",
                    imported["project_key"],
                    imported["import_id"],
                    imported["file_count"],
                    imported["repo_path"],
                )
                self._send_json(imported, status=HTTPStatus.CREATED)
                return

            if len(parts) == 3 and parts[0] == "pipelines" and parts[2] == "run":
                pipeline = run_pipeline(parts[1])
                self._send_json(_pipeline_to_dict(pipeline))
                return

            if len(parts) == 3 and parts[0] == "checkpoints" and parts[2] in {"approve", "reject"}:
                payload = self._read_json()
                note = (payload.get("note") or "") if isinstance(payload, dict) else ""
                context_patch = payload.get("context_patch") if isinstance(payload, dict) else None
                checkpoint = get_checkpoint(parts[1])
                if parts[2] == "approve":
                    pipeline = approve(
                        checkpoint.pipeline_id,
                        checkpoint_id=checkpoint.id,
                        context_patch=context_patch if isinstance(context_patch, dict) else None,
                        note=note,
                    )
                else:
                    pipeline = reject(checkpoint.pipeline_id, checkpoint_id=checkpoint.id, note=note)
                self._send_json(_pipeline_to_dict(pipeline))
                return

            self._send_json({"detail": "not found"}, status=HTTPStatus.NOT_FOUND)
        except KeyError:
            LOGGER.warning("POST %s not found", self.path)
            self._send_json({"detail": "not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:
            LOGGER.exception("POST %s failed", self.path)
            self._send_json({"detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("HTTP %s - %s", self.address_string(), format % args)


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    log_file = configure_logging()
    server = ThreadingHTTPServer((host, port), PipelineHTTPDemoHandler)
    print(f"API first demo server listening on http://{host}:{port}")
    print(f"Log file: {log_file}")
    print("Endpoints: POST /pipelines, POST /pipelines/{id}/run, POST /checkpoints/{id}/approve, POST /checkpoints/{id}/reject")
    LOGGER.info("API first demo server listening on http://%s:%s", host, port)
    LOGGER.info("Log file: %s", log_file)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        LOGGER.info("Server stopped by KeyboardInterrupt")
    finally:
        server.server_close()
        LOGGER.info("Server closed")


if __name__ == "__main__":
    host = os.getenv("API_DEMO_HOST", DEFAULT_HOST)
    port = int(os.getenv("API_DEMO_PORT", str(DEFAULT_PORT)))
    main(host=host, port=port)
