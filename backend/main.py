import hashlib
import os
import random
import re
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
try:
    from .workflow import ReliableAgentWorkflow
except ImportError:
    from workflow import ReliableAgentWorkflow

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
    return {"message": "✅", "requirement_id": req_id}


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
async def execute_stage_stream(req_id: str, stage_id: str, mock_error: bool = False):
    """
    这里我们将直接挂载写好的抗灾多路由 SSE 生成管道！
    """
    if req_id not in FAKE_DB["requirements"]:
        raise HTTPException(status_code=404, detail="REQ NOT FOUND")

    req_data = FAKE_DB["requirements"][req_id]

    # 核心接入智能体容灾编排
    generator = agent_workflow.execute_stage_stream(
        req_id, stage_id, req_data, mock_error
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@app.post("/api/v1/auth/send-code")
async def send_email_code(payload: SendCodeRequest):
    email = str(payload.email).strip().lower()
    purpose = payload.purpose.strip().lower() or "register"

    if purpose != "register":
        raise HTTPException(status_code=400, detail="仅支持 register 场景验证码")

    record = FAKE_DB["email_codes"].get(email)
    now = now_utc()
    if record and record.get("last_sent_at"):
        last_sent_at = datetime.fromisoformat(record["last_sent_at"])
        if (now - last_sent_at).total_seconds() < CODE_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=429,
                detail=f"发送过于频繁，请 {CODE_COOLDOWN_SECONDS} 秒后重试",
            )

    code = f"{random.randint(0, 999999):06d}"
    code_salt = secrets.token_hex(16)
    code_hash = hash_secret(code, code_salt)
    expires_at = now + timedelta(seconds=CODE_EXPIRE_SECONDS)

    try:
        send_verification_email(email, code)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"邮件发送失败: {exc}") from exc

    FAKE_DB["email_codes"][email] = {
        "email": email,
        "purpose": purpose,
        "code_salt": code_salt,
        "code_hash": code_hash,
        "expires_at": to_iso(expires_at),
        "attempt_count": 0,
        "used_at": None,
        "last_sent_at": to_iso(now),
        "created_at": to_iso(now),
    }

    return {
        "ok": True,
        "message": "验证码已发送，请查收邮箱。",
        "expires_in_seconds": CODE_EXPIRE_SECONDS,
    }


@app.post("/api/v1/auth/verify-code")
async def verify_email_code(payload: VerifyCodeRequest):
    email = str(payload.email).strip().lower()
    code = payload.code.strip()
    purpose = payload.purpose.strip().lower() or "register"

    if not re.fullmatch(r"\d{6}", code):
        raise HTTPException(status_code=400, detail="验证码必须是 6 位数字")

    record = FAKE_DB["email_codes"].get(email)
    if not record or record.get("purpose") != purpose:
        raise HTTPException(status_code=400, detail="请先发送验证码")

    if record.get("used_at") is not None:
        raise HTTPException(status_code=400, detail="验证码已被使用，请重新获取")

    expires_at = datetime.fromisoformat(record["expires_at"])
    if now_utc() > expires_at:
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")

    if record["attempt_count"] >= CODE_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="验证码尝试次数过多，请重新获取")

    expected_hash = record["code_hash"]
    calculated_hash = hash_secret(code, record["code_salt"])
    if calculated_hash != expected_hash:
        record["attempt_count"] += 1
        raise HTTPException(status_code=400, detail="验证码错误")

    return {"ok": True, "message": "验证码校验通过"}


@app.post("/api/v1/auth/register")
async def register_user(payload: RegisterRequest):
    email = str(payload.email).strip().lower()
    password = payload.password
    code = payload.code.strip()

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")

    if email in FAKE_DB["users"]:
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    await verify_email_code(
        VerifyCodeRequest(email=email, code=code, purpose="register")
    )

    now = now_utc()
    password_salt = secrets.token_hex(16)
    password_hash = hash_secret(password, password_salt)
    user_id = str(uuid.uuid4())

    FAKE_DB["users"][email] = {
        "id": user_id,
        "email": email,
        "display_name": email.split("@")[0] or "协作者",
        "password_salt": password_salt,
        "password_hash": password_hash,
        "created_at": to_iso(now),
        "updated_at": to_iso(now),
        "last_login_at": None,
        "status": "active",
        "role": "member",
    }

    code_record = FAKE_DB["email_codes"].get(email)
    if code_record:
        code_record["used_at"] = to_iso(now)

    return {
        "ok": True,
        "message": "注册成功",
        "user": {
            "id": user_id,
            "email": email,
            "display_name": FAKE_DB["users"][email]["display_name"],
        },
    }


@app.post("/api/v1/auth/login")
async def login_user(payload: LoginRequest):
    email = str(payload.email).strip().lower()
    password = payload.password

    user = FAKE_DB["users"].get(email)
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在，请先注册")

    if hash_secret(password, user["password_salt"]) != user["password_hash"]:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    user["last_login_at"] = to_iso(now_utc())

    return {
        "ok": True,
        "message": "登录成功",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user.get("display_name", "协作者"),
        },
    }


@app.get("/")
async def root_to_login():
    return RedirectResponse(url="/login/splash.html", status_code=307)


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
