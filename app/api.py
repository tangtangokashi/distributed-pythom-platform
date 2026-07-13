from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.deepseek import explain
from app.services.ml import MLService
from app.services.realtime import realtime

router = APIRouter(prefix="/api", tags=["platform"])


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "distributed-decision-platform"}


@router.get("/dashboard")
def dashboard() -> dict:
    return realtime.snapshot()


@router.get("/finance")
def finance() -> dict:
    snapshot = realtime.snapshot()
    ticks = snapshot["ticks"]
    latest = {symbol: next((x for x in reversed(ticks) if x["symbol"] == symbol), None) for symbol in realtime.symbols}
    predictions = [{"symbol": symbol, "current": item["price"], "forecast": realtime.ml.forecast(realtime.tick_count + 1, item["price"]), "risk": "高" if abs(item["change_pct"]) > 2.5 else "低"} for symbol, item in latest.items() if item]
    return {"ticks": ticks, "predictions": predictions, "alerts": [x for x in snapshot["alerts"] if x["domain"] == "finance"]}


@router.get("/ecommerce")
def ecommerce() -> dict:
    snapshot = realtime.snapshot()
    recommendations = [
        {"user": "U1012", "segment": realtime.ml.segment(1680, 8), "items": ["无线耳机", "智能手表", "咖啡机"]},
        {"user": "U1048", "segment": realtime.ml.segment(590, 4), "items": ["跑鞋", "护肤套装", "无线耳机"]},
    ]
    return {"kpis": snapshot["kpis"], "orders": snapshot["orders_feed"], "recommendations": recommendations, "alerts": [x for x in snapshot["alerts"] if x["domain"] == "ecommerce"]}


@router.get("/models")
def models() -> list[dict]:
    return MLService.catalogue()


@router.post("/simulation/start")
async def start_simulation() -> dict:
    from app.config import get_settings
    await realtime.start(get_settings().simulation_interval_seconds)
    return {"running": True}


@router.post("/simulation/stop")
async def stop_simulation() -> dict:
    await realtime.stop()
    return {"running": False}


@router.post("/simulation/step")
def step_simulation() -> dict:
    realtime.emit_once()
    return realtime.snapshot()


@router.post("/ai/explain")
async def ai_explain(request: AskRequest) -> dict:
    snapshot = realtime.snapshot()
    summary = f"用户问题：{request.question}\n实时指标：订单数 {snapshot['kpis']['orders']}，GMV ¥{snapshot['kpis']['gmv']:,.2f}，告警数 {snapshot['kpis']['alerts']}。最近告警：{snapshot['alerts'][0]['title'] if snapshot['alerts'] else '无'}。"
    try:
        return await explain(summary)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek 调用失败：{exc}") from exc

