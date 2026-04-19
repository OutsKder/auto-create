import asyncio
import json
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from workflow import ReliableAgentWorkflow

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FAKE_DB: Dict[str, dict] = {
    "requirements": {}
}

# 引入我们刚才写的智能体工作流（抗灾备级）
agent_workflow = ReliableAgentWorkflow("fallback_mocks.json")

class RequirementCreate(BaseModel):
    title: str
    background: str = ""
    goal: str = ""
    priority: str = "medium"

class AuditAction(BaseModel):
    action: str 
    note: str = ""

@app.post("/api/v1/pipeline/start")
async def start_pipeline(req: RequirementCreate):
    req_id = str(uuid.uuid4())
    FAKE_DB["requirements"][req_id] = {
        "id": req_id,
        "title": req.title,
        "background": req.background,
        "goal": req.goal,
        "priority": req.priority,
        "stages": {}
    }
    return {"message": "✅", "requirement_id": req_id}

@app.post("/api/v1/pipeline/{req_id}/stage/{stage_id}/audit")
async def audit_stage(req_id: str, stage_id: str, payload: AuditAction):
    if req_id not in FAKE_DB["requirements"]:
        raise HTTPException(status_code=404, detail="Not Found")
    
    FAKE_DB["requirements"][req_id]["stages"][stage_id] = {
        "status": payload.action,
        "human_note": payload.note
    }
    return {"status": "success", "message": f"节点 {stage_id} 获得权限"}

@app.get("/api/v1/pipeline/{req_id}/stage/{stage_id}/execute/stream")
async def execute_stage_stream(
    req_id: str, 
    stage_id: str, 
    mock_error: bool = False,
    title: str = "",
    background: str = "",
    goal: str = "",
    constraints: str = ""
):
    """
    这里我们将直接挂载写好的抗灾多路由 SSE 生成管道！
    """
    if req_id not in FAKE_DB["requirements"]:
        if title:
            # 服从前端发送的恢复参数，避免后端服务热刷新后丢失上下文导致无法重跑
            FAKE_DB["requirements"][req_id] = {
                "id": req_id, "title": title, "background": background,
                "goal": goal, "constraints": constraints
            }
        else:
            raise HTTPException(status_code=404, detail="REQ NOT FOUND")
    req_data = FAKE_DB["requirements"][req_id]
    
    # 核心接入智能体容灾编排
    generator = agent_workflow.execute_stage_stream(req_id, stage_id, req_data, mock_error)
    return StreamingResponse(generator, media_type="text/event-stream")