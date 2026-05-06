from __future__ import annotations

import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .pipeline import Pipeline
from .stage import Stage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "generated-projects"
PROJECTS_ROOT = PROJECT_ROOT / "projects"

STAGE_OUTPUT_KEYS = {
    "analysis": ["requirement_structured", "analysis_doc"],
    "design": ["design_doc"],
    "coding": ["code_diff"],
    "testing": ["test_report"],
    "review": ["review_result"],
    "delivery": ["delivery"],
}


def pipeline_dir(pipeline: Pipeline) -> Path:
    return OUTPUT_ROOT / pipeline.id


def workspace_dir(pipeline: Pipeline) -> Path:
    return pipeline_dir(pipeline) / "workspace"


def _safe_workspace_path(root: Path, file_path: str) -> Path:
    normalized = file_path.replace("\\", "/").strip()
    # Treat "/foo/bar" as workspace-relative path, not filesystem absolute path.
    if normalized.startswith("/"):
        normalized = normalized.lstrip("/")

    relative = Path(normalized)
    if relative.is_absolute():
        raise ValueError(f"absolute patch path is not allowed: {file_path}")

    target = (root / relative).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError(f"patch path escapes workspace: {file_path}")
    return target


def _expected_visible_text(pipeline: Pipeline) -> str:
    requirement = str(pipeline.context.get("requirement_raw") or "")
    quoted = re.search(r"[“\"]([^”\"]+)[”\"]", requirement)
    if quoted:
        return quoted.group(1).strip()

    structured = pipeline.context.get("requirement_structured") or {}
    if isinstance(structured, dict):
        for value in [structured.get("goal"), *(structured.get("features") or [])]:
            text = str(value or "")
            quoted = re.search(r"[「“\"]([^」”\"]+)[」”\"]", text)
            if quoted:
                return quoted.group(1).strip()

    return ""


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _safe_project_key(value: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|\s]+", "-", value.strip())
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:48] or "ai-generated-project"


def _project_title(pipeline: Pipeline) -> str:
    expected = _expected_visible_text(pipeline)
    if expected:
        return f"{expected}网页"

    requirement = str(pipeline.context.get("requirement_raw") or "").strip()
    if requirement:
        compact = re.sub(r"\s+", "", requirement)
        return compact[:24]

    return f"AI生成项目-{pipeline.id[:8]}"


def _next_version_dir(project_root: Path) -> tuple[str, Path]:
    versions_root = project_root / "versions"
    versions_root.mkdir(parents=True, exist_ok=True)
    existing = []
    for child in versions_root.iterdir():
        if child.is_dir():
            match = re.fullmatch(r"v(\d+)", child.name)
            if match:
                existing.append(int(match.group(1)))
    version = f"v{(max(existing) if existing else 0) + 1}"
    return version, versions_root / version


def _workspace_files(root: Path) -> List[Dict[str, Any]]:
    if not root.exists():
        return []
    files = []
    for path in root.rglob("*"):
        if path.is_file():
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size": path.stat().st_size,
                }
            )
    return files


def create_delivery_package(pipeline: Pipeline) -> Dict[str, Any]:
    """Create a user-facing delivery version and zip package."""

    workspace_root = Path(str(pipeline.context.get("workspace_dir") or workspace_dir(pipeline)))
    if not workspace_root.exists():
        raise FileNotFoundError(f"workspace does not exist: {workspace_root}")

    project_title = _project_title(pipeline)
    project_key = _safe_project_key(project_title)
    project_root = PROJECTS_ROOT / project_key
    version, version_root = _next_version_dir(project_root)
    version_root.mkdir(parents=True, exist_ok=True)

    delivered_workspace = version_root / "workspace"
    if delivered_workspace.exists():
        shutil.rmtree(delivered_workspace)
    shutil.copytree(workspace_root, delivered_workspace)

    test_report = pipeline.context.get("test_report") or {}
    acceptance_report = {
        "pipeline_id": pipeline.id,
        "project_title": project_title,
        "project_key": project_key,
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirement": pipeline.context.get("requirement_raw", ""),
        "test_passed": test_report.get("passed"),
        "checks": (test_report.get("workspace") or {}).get("checks", [])
        if isinstance(test_report, dict)
        else [],
    }

    manifest = {
        "pipeline_id": pipeline.id,
        "project_title": project_title,
        "project_key": project_key,
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requirement": pipeline.context.get("requirement_raw", ""),
        "entry_file": "workspace/index.html"
        if (delivered_workspace / "index.html").exists()
        else "",
        "files": _workspace_files(delivered_workspace),
    }

    _write_json(project_root / "project.json", {
        "project_title": project_title,
        "project_key": project_key,
        "latest_version": version,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    _write_json(version_root / "manifest.json", manifest)
    _write_json(version_root / "acceptance-report.json", acceptance_report)

    readme = "\n".join(
        [
            f"# {project_title}",
            "",
            f"- Version: {version}",
            f"- Pipeline: {pipeline.id}",
            f"- Requirement: {pipeline.context.get('requirement_raw', '')}",
            f"- Entry: {manifest.get('entry_file') or 'workspace/'}",
            f"- Test passed: {acceptance_report.get('test_passed')}",
            "",
            "## How to open",
            "",
            "Open `workspace/index.html` in a browser, or use the preview button in the console.",
            "",
        ]
    )
    (version_root / "README.md").write_text(readme, encoding="utf-8")

    zip_path = version_root / f"{project_key}-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in version_root.rglob("*"):
            if path == zip_path or path.is_dir():
                continue
            archive.write(path, path.relative_to(version_root).as_posix())

    entry_file = version_root / manifest["entry_file"] if manifest.get("entry_file") else None
    delivery_package = {
        "project_title": project_title,
        "project_key": project_key,
        "version": version,
        "version_dir": str(version_root),
        "workspace_dir": str(delivered_workspace),
        "entry_file": str(entry_file) if entry_file else "",
        "manifest_file": str(version_root / "manifest.json"),
        "acceptance_report_file": str(version_root / "acceptance-report.json"),
        "zip_file": str(zip_path),
        "download_url": f"/deliveries/{pipeline.id}/download",
        "preview_url": f"/deliveries/{pipeline.id}/preview",
        "files": manifest["files"],
    }
    pipeline.context["delivery_package"] = delivery_package
    return delivery_package


def reject_fallback_code_diff(pipeline: Pipeline) -> None:
    """Reject placeholder fallback patches so they cannot be delivered as real code."""

    code_diff = pipeline.context.get("code_diff") or {}
    patches = code_diff.get("patches") if isinstance(code_diff, dict) else None
    if not isinstance(patches, list):
        raise ValueError("code_diff.patches is missing or invalid")

    fallback_files = []
    for patch in patches:
        if not isinstance(patch, dict):
            continue
        patch_text = str(patch.get("patch") or "")
        if "Fallback content generated from design fallback" in patch_text:
            fallback_files.append(str(patch.get("file_path") or "unknown"))

    if fallback_files:
        raise ValueError(
            "CodeGenerator returned fallback placeholder content instead of complete files: "
            + ", ".join(fallback_files)
        )


def apply_code_diff_to_workspace(pipeline: Pipeline) -> Dict[str, Any]:
    """Materialize code_diff.patches into the pipeline workspace directory."""

    reject_fallback_code_diff(pipeline)
    code_diff = pipeline.context.get("code_diff") or {}
    patches = code_diff.get("patches") if isinstance(code_diff, dict) else None
    if not isinstance(patches, list):
        raise ValueError("code_diff.patches is missing or invalid")

    root = workspace_dir(pipeline)
    root.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for patch in patches:
        if not isinstance(patch, dict):
            results.append({"applied": False, "error": "invalid patch item"})
            continue

        file_path = str(patch.get("file_path") or "").strip()
        change_type = str(patch.get("change_type") or "").strip().lower()
        patch_format = str(patch.get("patch_format") or "").strip().lower()
        patch_text = str(patch.get("patch") or "")

        try:
            target = _safe_workspace_path(root, file_path)
            if change_type in {"create", "modify"} and patch_format == "full_content":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(patch_text, encoding="utf-8")
            elif change_type == "delete":
                if target.exists():
                    target.unlink()
            else:
                raise ValueError(f"unsupported patch operation: {change_type}/{patch_format}")

            results.append(
                {
                    "file_path": file_path,
                    "applied": True,
                    "target": str(target),
                    "change_type": change_type,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "file_path": file_path,
                    "applied": False,
                    "error": str(exc),
                    "change_type": change_type,
                }
            )

    applied_files = [item["target"] for item in results if item.get("applied") and item.get("target")]
    entry_file = next((path for path in applied_files if Path(path).name.lower() == "index.html"), None)
    entry_file = entry_file or (applied_files[0] if applied_files else None)
    workspace = {
        "root": str(root),
        "entry_file": entry_file,
        "applied_files": applied_files,
        "patch_results": results,
    }
    pipeline.context["workspace"] = workspace
    pipeline.context["workspace_dir"] = workspace["root"]
    if entry_file:
        pipeline.context["entry_file"] = entry_file
    pipeline.context["codebase"] = {
        "repo_name": f"pipeline-{pipeline.id}",
        "repo_path": workspace["root"],
        "branch": "main",
    }
    return workspace


def validate_workspace(pipeline: Pipeline) -> Dict[str, Any]:
    """Run deterministic checks against materialized workspace files."""

    workspace = pipeline.context.get("workspace") or {}
    entry_file = workspace.get("entry_file") or pipeline.context.get("entry_file")
    expected_text = _expected_visible_text(pipeline)
    checks: List[Dict[str, Any]] = []

    def add_check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    if not entry_file:
        add_check("entry_file_present", False, "entry_file is missing")
    else:
        entry_path = Path(str(entry_file))
        add_check("entry_file_exists", entry_path.exists(), str(entry_path))
        if entry_path.exists():
            content = entry_path.read_text(encoding="utf-8")
            body_match = re.search(r"<body[^>]*>([\s\S]*?)</body>", content, flags=re.I)
            visible_source = body_match.group(1) if body_match else content
            visible_text = re.sub(r"<style[\s\S]*?</style>", "", visible_source, flags=re.I)
            visible_text = re.sub(r"<script[\s\S]*?</script>", "", visible_text, flags=re.I)
            visible_text = re.sub(r"<[^>]+>", "", visible_text)
            visible_text = re.sub(r"\s+", "", visible_text)

            add_check("expected_text_present", bool(expected_text), expected_text)
            add_check("contains_expected_text", bool(expected_text) and expected_text in content, expected_text)
            add_check("visible_text_exact", bool(expected_text) and visible_text == expected_text, visible_text)
            add_check(
                "declares_utf8",
                "charset=\"UTF-8\"" in content or "charset=UTF-8" in content,
                "",
            )
            add_check(
                "no_external_resources",
                not bool(re.search(r"\b(src|href)=['\"]https?://", content, flags=re.I)),
                "",
            )

    passed = all(check["passed"] for check in checks)
    report = {
        "passed": passed,
        "checks": checks,
        "entry_file": entry_file,
        "workspace_dir": pipeline.context.get("workspace_dir"),
    }
    pipeline.context["workspace_test_report"] = report
    return report


def build_delivery_summary(pipeline: Pipeline) -> Dict[str, Any]:
    workspace = pipeline.context.get("workspace") or {}
    test_report = pipeline.context.get("test_report") or {}
    delivery_package = create_delivery_package(pipeline)
    summary = {
        "status": "ready" if test_report.get("passed") else "needs_attention",
        "project_title": delivery_package["project_title"],
        "project_key": delivery_package["project_key"],
        "version": delivery_package["version"],
        "workspace_dir": pipeline.context.get("workspace_dir"),
        "entry_file": workspace.get("entry_file") or pipeline.context.get("entry_file"),
        "applied_files": workspace.get("applied_files", []),
        "test_passed": test_report.get("passed"),
        "stage_artifacts": pipeline.context.get("stage_artifacts", {}),
        "delivery_package": delivery_package,
        "download_url": delivery_package["download_url"],
        "preview_url": delivery_package["preview_url"],
    }
    pipeline.context["delivery"] = summary
    return summary


def _stage_payload(pipeline: Pipeline, stage: Stage) -> Dict[str, Any]:
    keys = STAGE_OUTPUT_KEYS.get(stage.id, [])
    outputs = {key: pipeline.context.get(key) for key in keys if key in pipeline.context}
    return {
        "pipeline_id": pipeline.id,
        "stage": {
            "id": stage.id,
            "name": stage.name,
            "status": stage.status.value,
            "meta": stage.meta,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "outputs": outputs,
        "context": pipeline.context,
    }


def persist_stage_artifacts(pipeline: Pipeline, stage: Stage) -> Dict[str, str]:
    """Persist the current stage output and full context for local demo inspection."""

    pipeline_dir_value = pipeline_dir(pipeline)
    stages_dir = pipeline_dir_value / "stages"
    stages_dir.mkdir(parents=True, exist_ok=True)

    stage_file = stages_dir / f"{pipeline.current_stage_index + 1:02d}-{stage.id}.json"
    context_file = pipeline_dir_value / "context.json"
    summary_file = pipeline_dir_value / "README.md"
    artifact_paths = {
        "root": str(pipeline_dir_value),
        "stage_file": str(stage_file),
        "context_file": str(context_file),
        "summary_file": str(summary_file),
    }

    pipeline.context["artifact_dir"] = artifact_paths["root"]
    pipeline.context.setdefault("stage_artifacts", {})[stage.id] = artifact_paths
    _write_json(stage_file, _stage_payload(pipeline, stage))
    _write_json(context_file, pipeline.context)
    summary_file.write_text(
        "\n".join(
            [
                f"# Pipeline {pipeline.id}",
                "",
                f"- Requirement: {pipeline.context.get('requirement_raw', '')}",
                f"- Current stage: {stage.name} ({stage.id})",
                f"- Updated at: {datetime.now(timezone.utc).isoformat()}",
                f"- Workspace: {pipeline.context.get('workspace_dir', 'pending')}",
                f"- Entry file: {pipeline.context.get('entry_file', 'pending')}",
                "",
                "## Stage Artifacts",
                f"- `{stage_file.relative_to(pipeline_dir_value).as_posix()}`",
                f"- `{context_file.relative_to(pipeline_dir_value).as_posix()}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return artifact_paths
