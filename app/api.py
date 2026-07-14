from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth import create_access_token, get_current_user, hash_password, verify_password
from app.services.deepseek import explain
from app.services.ml import MLService
from app.services.realtime import realtime

router = APIRouter(prefix="/api", tags=["platform"])


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("姓名至少需要 2 个字符")
        return value

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("请输入有效的邮箱地址")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)


def user_payload(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "created_at": user.created_at.isoformat()}


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "distributed-decision-platform"}


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(User).where(User.email == request.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已经注册")
    user = User(name=request.name, email=request.email, password_hash=hash_password(request.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已经注册") from exc
    db.refresh(user)
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user_payload(user)}


@router.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == request.email.strip().lower()))
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已停用")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user_payload(user)}


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return user_payload(user)


@router.get("/dashboard")
def dashboard(_: User = Depends(get_current_user)) -> dict:
    return realtime.snapshot()


@router.get("/finance")
def finance(_: User = Depends(get_current_user)) -> dict:
    snapshot = realtime.snapshot()
    ticks = snapshot["ticks"]
    latest = {symbol: next((x for x in reversed(ticks) if x["symbol"] == symbol), None) for symbol in realtime.symbols}
    predictions = [{"symbol": symbol, "current": item["price"], "forecast": realtime.ml.forecast(realtime.tick_count + 1, item["price"]), "risk": "高" if abs(item["change_pct"]) > 2.5 else "低"} for symbol, item in latest.items() if item]
    return {"ticks": ticks, "predictions": predictions, "alerts": [x for x in snapshot["alerts"] if x["domain"] == "finance"]}


@router.get("/ecommerce")
def ecommerce(_: User = Depends(get_current_user)) -> dict:
    snapshot = realtime.snapshot()
    recommendations = [
        {"user": "U1012", "segment": realtime.ml.segment(1680, 8), "items": ["无线耳机", "智能手表", "咖啡机"]},
        {"user": "U1048", "segment": realtime.ml.segment(590, 4), "items": ["跑鞋", "护肤套装", "无线耳机"]},
    ]
    return {"kpis": snapshot["kpis"], "orders": snapshot["orders_feed"], "recommendations": recommendations, "alerts": [x for x in snapshot["alerts"] if x["domain"] == "ecommerce"]}


@router.get("/models")
def models(_: User = Depends(get_current_user)) -> list[dict]:
    return MLService.catalogue()


@router.post("/simulation/start")
async def start_simulation(_: User = Depends(get_current_user)) -> dict:
    from app.config import get_settings
    await realtime.start(get_settings().simulation_interval_seconds)
    return {"running": True}


@router.post("/simulation/stop")
async def stop_simulation(_: User = Depends(get_current_user)) -> dict:
    await realtime.stop()
    return {"running": False}


@router.post("/simulation/step")
def step_simulation(_: User = Depends(get_current_user)) -> dict:
    realtime.emit_once()
    return realtime.snapshot()


@router.post("/ai/explain")
async def ai_explain(request: AskRequest, _: User = Depends(get_current_user)) -> dict:
    snapshot = realtime.snapshot()
    summary = f"用户问题：{request.question}\n实时指标：订单数 {snapshot['kpis']['orders']}，GMV ¥{snapshot['kpis']['gmv']:,.2f}，告警数 {snapshot['kpis']['alerts']}。最近告警：{snapshot['alerts'][0]['title'] if snapshot['alerts'] else '无'}。"
    try:
        return await explain(summary)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek 调用失败：{exc}") from exc

