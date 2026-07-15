from __future__ import annotations

import re
import secrets
import smtplib
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.models import Alert, EmailVerification, PasswordChangeVerification, User
from app.services.auth import create_access_token, get_current_user, hash_email_code, hash_password, verify_email_code, verify_password
from app.services.deepseek import explain, generate_operating_report, translate_review_to_chinese
from app.services.email import send_verification_email
from app.services.ml import MLService
from app.services.realtime import realtime

router = APIRouter(prefix="/api", tags=["platform"])


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class ReviewTranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


class ScenarioRequest(BaseModel):
    scenario: str = Field(pattern=r"^(market_shock|large_order|negative_reviews)$")


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    verification_code: str = Field(pattern=r"^\d{6}$")

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


class EmailCodeRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("请输入有效的邮箱地址")
        return value


class ProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    current_password: str | None = Field(default=None, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
    verification_code: str | None = Field(default=None, pattern=r"^\d{6}$")

    @field_validator("name")
    @classmethod
    def clean_profile_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("姓名至少需要 2 个字符")
        return value


def user_payload(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "created_at": user.created_at.isoformat()}


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "distributed-decision-platform"}


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(User).where(User.email == request.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已经注册")
    verification = db.scalar(select(EmailVerification).where(EmailVerification.email == request.email))
    if not verification or verification.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码不存在或已过期，请重新获取")
    if verification.attempts >= 5:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="验证码错误次数过多，请重新获取")
    if not verify_email_code(request.email, request.verification_code, verification.code_hash):
        verification.attempts += 1
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱验证码错误")
    user = User(name=request.name, email=request.email, password_hash=hash_password(request.password))
    db.add(user)
    db.delete(verification)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已经注册") from exc
    db.refresh(user)
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user_payload(user)}


@router.post("/auth/email-code")
def send_email_code(request: EmailCodeRequest, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(User).where(User.email == request.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已经注册")
    settings = get_settings()
    now = datetime.utcnow()
    verification = db.scalar(select(EmailVerification).where(EmailVerification.email == request.email))
    if verification and (now - verification.sent_at).total_seconds() < settings.email_code_resend_seconds:
        wait = settings.email_code_resend_seconds - int((now - verification.sent_at).total_seconds())
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"请在 {wait} 秒后重新获取验证码")
    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        send_verification_email(request.email, code)
    except (RuntimeError, OSError, smtplib.SMTPException) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if verification:
        verification.code_hash = hash_email_code(request.email, code)
        verification.attempts = 0
        verification.sent_at = now
        verification.expires_at = now + timedelta(minutes=settings.email_code_expire_minutes)
    else:
        db.add(EmailVerification(
            email=request.email,
            code_hash=hash_email_code(request.email, code),
            expires_at=now + timedelta(minutes=settings.email_code_expire_minutes),
            sent_at=now,
        ))
    db.commit()
    return {"message": "验证码已发送，请检查邮箱", "expires_in": settings.email_code_expire_minutes * 60}


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


@router.patch("/auth/me")
def update_profile(request: ProfileUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if request.new_password:
        if not request.current_password or not verify_password(request.current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确，无法修改密码")
        verification = db.scalar(select(PasswordChangeVerification).where(PasswordChangeVerification.user_id == user.id))
        if not verification or verification.expires_at < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码修改验证码不存在或已过期，请重新获取")
        if verification.attempts >= 5:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="验证码错误次数过多，请重新获取")
        if not request.verification_code or not verify_email_code(user.email, request.verification_code, verification.code_hash):
            verification.attempts += 1; db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码修改验证码错误")
        user.password_hash = hash_password(request.new_password)
        db.delete(verification)
    user.name = request.name
    db.commit(); db.refresh(user)
    return user_payload(user)


@router.post("/auth/password-change-code")
def send_password_change_code(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    settings = get_settings(); now = datetime.utcnow()
    verification = db.scalar(select(PasswordChangeVerification).where(PasswordChangeVerification.user_id == user.id))
    if verification and (now - verification.sent_at).total_seconds() < settings.email_code_resend_seconds:
        wait = settings.email_code_resend_seconds - int((now - verification.sent_at).total_seconds())
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"请在 {wait} 秒后重新获取验证码")
    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        send_verification_email(user.email, code)
    except (RuntimeError, OSError, smtplib.SMTPException) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if verification:
        verification.code_hash = hash_email_code(user.email, code); verification.attempts = 0; verification.sent_at = now; verification.expires_at = now + timedelta(minutes=settings.email_code_expire_minutes)
    else:
        db.add(PasswordChangeVerification(user_id=user.id, code_hash=hash_email_code(user.email, code), attempts=0, sent_at=now, expires_at=now + timedelta(minutes=settings.email_code_expire_minutes)))
    db.commit()
    return {"message": "密码修改验证码已发送至登录邮箱", "expires_in": settings.email_code_expire_minutes * 60}


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


@router.get("/orders/{order_code}/review")
async def order_review(order_code: str, _: User = Depends(get_current_user)) -> dict:
    try:
        payload = realtime.order_review(order_code)
        for review in payload["reviews"][:3]:
            try:
                review["translation"] = await translate_review_to_chinese(review["text"])
            except Exception:
                review["translation"] = None
        return payload
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该订单不在当前回放窗口中，请从实时订单列表重新选择") from exc


@router.get("/recommendations/{user_id}")
def recommendations(user_id: str, _: User = Depends(get_current_user)) -> dict:
    return realtime.recommendations(user_id)


@router.get("/models")
def models(_: User = Depends(get_current_user)) -> list[dict]:
    return MLService.catalogue()


@router.get("/alerts")
def all_alerts(limit: int = 100, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    records = db.scalars(select(Alert).order_by(Alert.created_at.desc()).limit(min(max(limit, 1), 200))).all()
    return [{"id": item.id, "domain": item.domain, "severity": item.severity, "title": item.title, "detail": item.detail, "time": item.created_at.strftime("%Y-%m-%d %H:%M:%S")} for item in records]


@router.get("/sentiment")
def sentiment(_: User = Depends(get_current_user)) -> dict:
    return {
        "chinese": realtime.chinese_sentiment,
        "olist": realtime.sentiment,
    }


@router.post("/reviews/translate")
async def translate_review(request: ReviewTranslationRequest, _: User = Depends(get_current_user)) -> dict:
    try:
        translation = await translate_review_to_chinese(request.text.strip())
        if not translation:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="DeepSeek 翻译服务未配置或当前评价没有可翻译文本")
        return {"translation": translation}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"评论翻译失败：{exc}") from exc


@router.get("/ai/status")
def ai_status(_: User = Depends(get_current_user)) -> dict:
    settings = get_settings()
    return {
        "provider": "DeepSeek" if settings.deepseek_api_key else "本地规则引擎",
        "model": settings.deepseek_model if settings.deepseek_api_key else "未配置 DeepSeek API Key",
        "connected": bool(settings.deepseek_api_key),
    }


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


@router.post("/simulation/inject")
def inject_scenario(request: ScenarioRequest, _: User = Depends(get_current_user)) -> dict:
    try:
        return realtime.inject_scenario(request.scenario)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/ai/explain")
async def ai_explain(request: AskRequest, _: User = Depends(get_current_user)) -> dict:
    snapshot = realtime.snapshot()
    summary = f"用户问题：{request.question}\n实时指标：Olist 回放订单数 {snapshot['kpis']['orders']}，GMV R${snapshot['kpis']['gmv']:,.2f}，告警数 {snapshot['kpis']['alerts']}。最近告警：{snapshot['alerts'][0]['title'] if snapshot['alerts'] else '无'}。"
    try:
        return await explain(summary)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek 调用失败：{exc}") from exc


@router.post("/reports/generate")
async def generate_report(_: User = Depends(get_current_user)) -> dict:
    snapshot = realtime.snapshot()
    sentiment = realtime.sentiment
    alerts = snapshot["alerts"][:5]
    exercises = snapshot["exercise_events"][:5]
    alerts_text = "; ".join(f"{item['title']}（{item['detail']}）" for item in alerts) or "无"
    exercises_text = "; ".join(f"{item['title']}（{item['detail']}）" for item in exercises) or "无"
    context = (
        f"报告生成时间：{datetime.now():%Y-%m-%d %H:%M}\n"
        f"数据范围：真实历史数据回放（金融 AAPL/TSLA/NVDA；电商 Olist 订单及其关联评价）。\n"
        f"关键指标：订单 {snapshot['kpis']['orders']} 笔，GMV R${snapshot['kpis']['gmv']:,.2f}，活跃用户估算 {snapshot['kpis']['active_users']}，风险告警 {snapshot['kpis']['alerts']}。\n"
        f"Olist 订单评价情感：正面 {sentiment['counts'].get('正面', 0)}，负面 {sentiment['counts'].get('负面', 0)}，中性 {sentiment['counts'].get('中性', 0)}。\n"
        f"近期告警：{alerts_text}。\n"
        f"本轮控制演练：{exercises_text}。"
    )
    try:
        report = await generate_operating_report(context)
        return {**report, "generated_at": datetime.now().isoformat(), "context": context}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"报告生成失败：{exc}") from exc

