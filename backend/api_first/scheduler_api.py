from typing import Any, Dict
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pipeline import Pipeline, PipelineStatus
from .service import (
    advance_one_stage,
    approve,
    auto_advance_pipeline,
    create_pipeline,
    get_pipeline,
    get_checkpoint,
    list_pipelines,
    run_agent_stages,
    reject,
    run_pipeline,
)
from .dispatcher import dispatch_stage

app = FastAPI(title="Pipeline Scheduler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ActionRequest(BaseModel):
    note: str = ""

class CreatePipelineRequest(BaseModel):
    requirement_raw: str
    context: Dict[str, Any] = {}


def _pipeline_to_dict(pipeline: Pipeline) -> Dict[str, Any]:
    current_stage = pipeline.current_stage()
    checkpoint = pipeline.current_checkpoint()

    if pipeline.status in (PipelineStatus.CREATED, PipelineStatus.RUNNING):
        next_http: Any = {
            "method": "POST",
            "path": f"/pipelines/{pipeline.id}/run",
            "description": "推进当前 stage 并等待后台 agent 执行完成",
        }
    elif pipeline.status == PipelineStatus.WAITING_APPROVAL and checkpoint:
        next_http = {
            "approve": {
                "method": "POST",
                "path": f"/checkpoints/{checkpoint.id}/approve",
                "description": "审批通过当前 checkpoint",
            },
            "reject": {
                "method": "POST",
                "path": f"/checkpoints/{checkpoint.id}/reject",
                "description": "审批驳回当前 checkpoint",
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
        "context": pipeline.context
        ,
        "next_http": next_http,
    }


@app.post("/pipelines")
def post_pipelines(req: CreatePipelineRequest) -> Dict[str, Any]:
    context = req.context
    context["requirement_raw"] = req.requirement_raw
    pipeline = create_pipeline(context=context)
    return _pipeline_to_dict(pipeline)


@app.get("/pipelines")
def list_pipelines_api() -> Dict[str, Any]:
    pipelines = list_pipelines()
    return {
        "total": len(pipelines),
        "items": [_pipeline_to_dict(pipeline) for pipeline in pipelines],
    }


async def run_pipeline_background(pipeline_id: str) -> None:
    """后台异步执行pipeline的具体Stage"""
    try:
        pipeline = get_pipeline(pipeline_id)
        # 不再用 while 循环，一次只跑到需要人工审批即可。
        # 实际如果是多Agent可能还需要根据配置循环，这里我们阶段化执行：
        await dispatch_stage(pipeline)
    except Exception as e:
        print(f"Pipeline执行出错: {str(e)}")

@app.post("/pipelines/{pipeline_id}/run")
async def run_pipeline_api(pipeline_id: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    try:
        pipeline = get_pipeline(pipeline_id)
        # 先启动pipeline，立刻返回结果
        if pipeline.status == PipelineStatus.CREATED:
            pipeline.start()
        elif pipeline.status == PipelineStatus.WAITING_APPROVAL:
            # 如果当前状态是 WAITING_APPROVAL，说明用户未通过审批端点调用而是错误地再次调了 run
            pass # 由dispatcher处理或抛错，这里放行保持幂等
            
        # 添加后台任务执行Agent逻辑
        background_tasks.add_task(run_pipeline_background, pipeline_id)
        return _pipeline_to_dict(pipeline)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="pipeline not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc





@app.post("/pipelines/{pipeline_id}/auto-advance")
def auto_advance_pipeline_api(pipeline_id: str) -> Dict[str, Any]:
    try:
        pipeline = auto_advance_pipeline(pipeline_id)
        return _pipeline_to_dict(pipeline)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="pipeline not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# 内部调试接口，不对外公开
# @app.post("/pipelines/{pipeline_id}/advance-one-stage")
# def advance_one_stage_api(pipeline_id: str) -> Dict[str, Any]:
#     try:
#         pipeline = advance_one_stage(pipeline_id)
#         return _pipeline_to_dict(pipeline)
#     except KeyError as exc:
#         raise HTTPException(status_code=404, detail="pipeline not found") from exc
#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc)) from exc


# 已废弃，请使用 /checkpoints/{checkpoint_id}/reject 接口
# @app.post("/pipelines/{pipeline_id}/reject")
# def reject_stage_api(pipeline_id: str, req: ActionRequest) -> Dict[str, Any]:
#     try:
#         pipeline = reject(pipeline_id, note=req.note)
#         return _pipeline_to_dict(pipeline)
#     except KeyError as exc:
#         raise HTTPException(status_code=404, detail="pipeline not found") from exc
#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/pipelines/{pipeline_id}")
def get_pipeline_api(pipeline_id: str) -> Dict[str, Any]:
    try:
        pipeline = get_pipeline(pipeline_id)
        return _pipeline_to_dict(pipeline)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="pipeline not found") from exc


@app.get("/pipelines/{pipeline_id}/current-stage")
def get_current_stage_api(pipeline_id: str) -> Dict[str, Any]:
    try:
        pipeline = get_pipeline(pipeline_id)
        current_stage = pipeline.current_stage()
        if current_stage is None:
            return {"pipeline_id": pipeline.id, "current_stage": None}
        return {
            "pipeline_id": pipeline.id,
            "current_stage": {
                "id": current_stage.id,
                "name": current_stage.name,
                "status": current_stage.status.value,
                "meta": current_stage.meta,
            },
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="pipeline not found") from exc


@app.post("/checkpoints/{checkpoint_id}/approve")
def approve_checkpoint_api(checkpoint_id: str, req: ActionRequest | None = None) -> Dict[str, Any]:
    try:
        checkpoint = get_checkpoint(checkpoint_id)
        pipeline = approve(checkpoint.pipeline_id, checkpoint_id=checkpoint.id)
        if req and req.note:
            checkpoint.note = req.note
        return _pipeline_to_dict(pipeline)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="checkpoint not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/checkpoints/{checkpoint_id}/reject")
def reject_checkpoint_api(checkpoint_id: str, req: ActionRequest | None = None) -> Dict[str, Any]:
    try:
        checkpoint = get_checkpoint(checkpoint_id)
        note = req.note if req and req.note else ""
        pipeline = reject(checkpoint.pipeline_id, checkpoint_id=checkpoint.id, note=note)
        return _pipeline_to_dict(pipeline)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="checkpoint not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
