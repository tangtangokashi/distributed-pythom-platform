from __future__ import annotations

import asyncio
import random
from collections import deque
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Alert, EcommerceOrder, MarketTick
from app.services.ml import MLService


class RealtimeService:
    products = [("智能手表", "数码"), ("无线耳机", "数码"), ("咖啡机", "家居"), ("跑鞋", "运动"), ("护肤套装", "美妆")]
    regions = ["华东", "华南", "华北", "西南", "海外"]
    symbols = ["AAPL", "TSLA", "NVDA"]

    def __init__(self) -> None:
        self.ml = MLService()
        self.running = False
        self.task: asyncio.Task | None = None
        self.tick_count = 0
        self.prices = {"AAPL": 192.4, "TSLA": 248.2, "NVDA": 135.7}
        self.recent_ticks: deque[dict] = deque(maxlen=80)
        self.recent_orders: deque[dict] = deque(maxlen=20)
        self.kafka_messages = 0
        self.spark_latency = 36

    def seed(self) -> None:
        with SessionLocal() as db:
            if db.scalar(select(func.count()).select_from(MarketTick)):
                return
            for index in range(35):
                for symbol, base in self.prices.items():
                    price = round(base * (1 + random.uniform(-0.012, 0.012)), 2)
                    tick = MarketTick(symbol=symbol, price=price, open_price=base, volume=random.randint(650_000, 1_350_000), change_pct=round((price - base) / base * 100, 2))
                    db.add(tick)
                    self.recent_ticks.append(self._tick_dict(tick, index))
            db.commit()

    async def start(self, interval: float) -> None:
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._loop(interval))

    async def stop(self) -> None:
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

    async def _loop(self, interval: float) -> None:
        while self.running:
            self.emit_once()
            await asyncio.sleep(interval)

    def emit_once(self) -> None:
        self.tick_count += 1
        symbol = self.symbols[self.tick_count % len(self.symbols)]
        previous = self.prices[symbol]
        shock = random.choice([0, 0, 0, 0, random.uniform(-0.045, 0.045)])
        change = random.uniform(-0.006, 0.006) + shock
        price = round(previous * (1 + change), 2)
        volume = random.randint(600_000, 1_450_000) + (800_000 if abs(shock) > 0.025 else 0)
        self.prices[symbol] = price
        is_anomaly, risk = self.ml.market_risk(change * 100, volume)
        with SessionLocal() as db:
            tick = MarketTick(symbol=symbol, price=price, open_price=previous, volume=volume, change_pct=round(change * 100, 2))
            db.add(tick)
            if is_anomaly:
                self._alert(db, "finance", "高" if abs(change) > .028 else "中", f"{symbol} 价格波动异常", f"当前涨跌 {change * 100:.2f}%，成交量 {volume:,}，风险分数 {risk}")
            product, category = random.choice(self.products)
            amount = round(random.uniform(45, 680) * (4 if self.tick_count % 29 == 0 else 1), 2)
            order_risky, order_score = self.ml.order_risk(amount, self.products.index((product, category)))
            order = EcommerceOrder(order_code=f"DEMO-{datetime.now():%H%M%S}-{self.tick_count:04d}", user_id=f"U{random.randint(1001, 1120)}", product=product, category=category, region=random.choice(self.regions), amount=amount, is_anomaly=order_risky)
            db.add(order)
            if order_risky:
                self._alert(db, "ecommerce", "高", "疑似异常订单", f"订单金额 ¥{amount:,.2f}，商品 {product}，异常分数 {order_score}")
            db.commit()
            self.recent_ticks.append(self._tick_dict(tick, self.tick_count))
            self.recent_orders.appendleft(self._order_dict(order))
        self.kafka_messages += 2
        self.spark_latency = random.randint(24, 68)

    @staticmethod
    def _alert(db: Session, domain: str, severity: str, title: str, detail: str) -> None:
        db.add(Alert(domain=domain, severity=severity, title=title, detail=detail))

    @staticmethod
    def _tick_dict(tick: MarketTick, _: int = 0) -> dict:
        created_at = tick.created_at or datetime.utcnow()
        return {"symbol": tick.symbol, "price": tick.price, "volume": tick.volume, "change_pct": tick.change_pct, "time": created_at.strftime("%H:%M:%S")}

    @staticmethod
    def _order_dict(order: EcommerceOrder) -> dict:
        created_at = order.created_at or datetime.utcnow()
        return {"order_code": order.order_code, "user_id": order.user_id, "product": order.product, "category": order.category, "region": order.region, "amount": order.amount, "is_anomaly": order.is_anomaly, "time": created_at.strftime("%H:%M:%S")}

    def snapshot(self) -> dict:
        with SessionLocal() as db:
            orders_today = db.scalar(select(func.count()).select_from(EcommerceOrder)) or 0
            gmv = db.scalar(select(func.coalesce(func.sum(EcommerceOrder.amount), 0))) or 0
            alerts = db.scalars(select(Alert).order_by(Alert.created_at.desc()).limit(8)).all()
            return {
                "running": self.running,
                "kpis": {"orders": orders_today, "gmv": round(gmv, 2), "active_users": min(120, 24 + orders_today // 2), "alerts": len(alerts)},
                "ticks": list(self.recent_ticks)[-45:],
                "orders_feed": list(self.recent_orders),
                "alerts": [{"id": x.id, "domain": x.domain, "severity": x.severity, "title": x.title, "detail": x.detail, "time": x.created_at.strftime("%H:%M:%S")} for x in alerts],
                "stream": {"kafka_messages": self.kafka_messages, "throughput": round(2 / max(0.1, 1), 1), "spark_latency": self.spark_latency},
                "nodes": [{"name": "节点 1 · 主控", "status": "healthy", "role": "Web / PostgreSQL / Spark Master"}, {"name": "节点 2 · 计算 A", "status": "healthy", "role": "Kafka / Spark Worker / MinIO"}, {"name": "节点 3 · 计算 B", "status": "healthy", "role": "Kafka / Spark Worker / Redis"}],
            }


realtime = RealtimeService()
