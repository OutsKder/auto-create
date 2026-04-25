<<<<<<< HEAD
import os
import asyncio
import json
=======
import hashlib
import os
import random
import re
import secrets
import smtplib
>>>>>>> 170a7f2c4b197844a5a1e0442f21f7348024ba63
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
<<<<<<< HEAD
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from workflow import ReliableAgentWorkflow
=======
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
try:
    from .workflow import ReliableAgentWorkflow
except ImportError:
    from workflow import ReliableAgentWorkflow
>>>>>>> 170a7f2c4b197844a5a1e0442f21f7348024ba63

app = FastAPI()
BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent
load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FAKE_DB: Dict[str, dict] = {
    "requirements": {},
    "users": {},
    "email_codes": {},
}

CODE_EXPIRE_SECONDS = int(os.getenv("EMAIL_CODE_EXPIRE_SECONDS", "300"))
CODE_COOLDOWN_SECONDS = int(os.getenv("EMAIL_CODE_COOLDOWN_SECONDS", "60"))
CODE_MAX_ATTEMPTS = int(os.getenv("EMAIL_CODE_MAX_ATTEMPTS", "5"))

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "false").lower() == "true"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def hash_secret(secret: str, salt: str) -> str:
    payload = f"{salt}:{secret}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def send_verification_email(target_email: str, code: str) -> None:
    if not SMTP_HOST or not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM:
        raise RuntimeError(
            "SMTP 未配置完整。请设置 SMTP_HOST/SMTP_PORT/SMTP_USERNAME/SMTP_PASSWORD/SMTP_FROM。"
        )

    message = EmailMessage()
    message["Subject"] = "【织界引擎】邮箱验证码"
    message["From"] = SMTP_FROM
    message["To"] = target_email
    message.set_content(
        (
            "你正在进行织界引擎账号注册。\n\n"
            f"验证码：{code}\n"
            f"有效期：{CODE_EXPIRE_SECONDS // 60} 分钟\n\n"
            "若非本人操作，请忽略本邮件。"
        ),
        subtype="plain",
        charset="utf-8",
    )

    if SMTP_USE_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        if SMTP_USE_TLS:
            server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)


# 引入我们刚才写的智能体工作流（抗灾备级）
agent_workflow = ReliableAgentWorkflow(str(BACKEND_DIR / "fallback_mocks.json"))


class RequirementCreate(BaseModel):
    title: str
    background: str = ""
    goal: str = ""
    priority: str = "medium"


class AuditAction(BaseModel):
    action: str
    note: str = ""


class SendCodeRequest(BaseModel):
    email: EmailStr
    purpose: str = "register"


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str
    purpose: str = "register"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    code: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@app.post("/api/v1/pipeline/start")
async def start_pipeline(req: RequirementCreate):
    req_id = str(uuid.uuid4())
    FAKE_DB["requirements"][req_id] = {
        "id": req_id,
        "title": req.title,
        "background": req.background,
        "goal": req.goal,
        "priority": req.priority,
        "stages": {},
    }
    return {"message": "�?, "requirement_id": req_id}


@app.post("/api/v1/pipeline/{req_id}/stage/{stage_id}/audit")
async def audit_stage(req_id: str, stage_id: str, payload: AuditAction):
    if req_id not in FAKE_DB["requirements"]:
        raise HTTPException(status_code=404, detail="Not Found")

    FAKE_DB["requirements"][req_id]["stages"][stage_id] = {
        "status": payload.action,
        "human_note": payload.note,
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
    这里我们将直接挂载写好的抗灾多路�?SSE 生成管道�?
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
    
    # 核心接入智能体容灾编�?
    generator = agent_workflow.execute_stage_stream(req_id, stage_id, req_data, mock_error)
    return StreamingResponse(generator, media_type="text/event-stream")
