from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Alert, EcommerceOrder, MarketTick
from app.services.datasets import RealDatasetRepository
from app.services.ml import MLService


class RealtimeService:
    symbols = ["AAPL", "TSLA", "NVDA"]

    def __init__(self) -> None:
        self.ml = MLService()
        self.datasets = RealDatasetRepository()
        self.running = False
        self.task: asyncio.Task | None = None
        self.tick_count = 0
        self.market_events: list[dict] = []
        self.order_events: list[dict] = []
        self.market_cursor = 0
        self.order_cursor = 0
        self.recent_ticks: deque[dict] = deque(maxlen=80)
        self.recent_orders: deque[dict] = deque(maxlen=20)
        self.kafka_messages = 0
        self.spark_latency = 36
        self.sentiment = self.datasets.review_summary()
        self.chinese_sentiment = self.datasets.chinese_product_review_summary()
        self.order_source_lookup: dict[str, dict] = {}
        self.exercise_events: deque[dict] = deque(maxlen=12)

    def seed(self) -> None:
        with SessionLocal() as db:
            self.market_events = self.datasets.market_events()
            self.order_events = self.datasets.order_events()
            self.sentiment = self.datasets.review_summary()
            self.chinese_sentiment = self.datasets.chinese_product_review_summary()
            if not self.market_events or not self.order_events:
                raise RuntimeError("未发现真实数据集。请确认 data/finance 与 data/olist/raw 已下载并解压。")
            # The previous release generated random rows. Reset only demo-domain tables so
            # the dashboard always truthfully replays the checked-in real datasets.
            db.execute(delete(Alert)); db.execute(delete(EcommerceOrder)); db.execute(delete(MarketTick)); db.commit()
            self.recent_ticks.clear(); self.recent_orders.clear(); self.order_source_lookup.clear(); self.exercise_events.clear(); self.tick_count = 0; self.market_cursor = 0; self.order_cursor = 0; self.kafka_messages = 0
        for _ in range(45):
            self.emit_once()

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
        if not self.market_events or not self.order_events:
            return
        self.tick_count += 1
        market = self.market_events[self.market_cursor % len(self.market_events)]; self.market_cursor += 1
        order_source = self.order_events[self.order_cursor % len(self.order_events)]; self.order_cursor += 1
        is_anomaly, risk = self.ml.market_risk(market["change_pct"], market["volume"])
        with SessionLocal() as db:
            tick = MarketTick(symbol=market["symbol"], price=market["price"], open_price=market["open_price"], volume=market["volume"], change_pct=market["change_pct"])
            db.add(tick)
            if is_anomaly:
                self._alert(db, "finance", "高" if abs(market["change_pct"]) > 2.8 else "中", f"{market['symbol']} 历史行情波动异常", f"来源日期 {market['source_date']}，涨跌 {market['change_pct']:.2f}%，成交量 {market['volume']:,}，风险分数 {risk}")
            order_risky, order_score = self.ml.order_risk(order_source["amount"], abs(hash(order_source["category"])) % 6)
            order = EcommerceOrder(order_code=f"OLIST-{order_source['source_id'][:8]}-{self.tick_count:06d}", user_id=order_source["user_id"], product=order_source["product"], category=order_source["category"], region=order_source["region"], amount=order_source["amount"], is_anomaly=order_risky)
            db.add(order)
            if order_risky:
                self._alert(db, "ecommerce", "高", "Olist 异常订单候选", f"真实订单金额 R${order_source['amount']:,.2f}，品类 {order_source['category']}，异常分数 {order_score}")
            db.commit()
            self.recent_ticks.append(self._tick_dict(tick, self.tick_count))
            order_payload = self._order_dict(order)
            order_payload["source_order_id"] = order_source["source_id"]
            self.order_source_lookup[order.order_code] = {**order_payload, "source_time": order_source["source_time"]}
            self.recent_orders.appendleft(order_payload)
        self.kafka_messages += 2
        self.spark_latency = 32 + self.tick_count % 19

    def inject_scenario(self, scenario: str) -> dict:
        """Inject a clearly labelled training event on top of the real historical replay."""
        if scenario not in {"market_shock", "large_order", "negative_reviews"}:
            raise ValueError("不支持的演练场景")
        if not self.market_events or not self.order_events:
            raise RuntimeError("真实数据尚未加载")
        self.tick_count += 1
        now = datetime.utcnow()
        with SessionLocal() as db:
            if scenario == "market_shock":
                source = self.market_events[self.market_cursor % len(self.market_events)]; self.market_cursor += 1
                direction = -1 if self.tick_count % 2 else 1
                change_pct = round(direction * 6.8, 2)
                price = round(source["price"] * (1 + change_pct / 100), 4)
                volume = int(source["volume"] * 3.2)
                tick = MarketTick(symbol=source["symbol"], price=price, open_price=source["price"], volume=volume, change_pct=change_pct)
                db.add(tick)
                self._alert(db, "finance", "高", "控制事件：市场剧烈波动", f"控制事件（非原始行情）：{source['symbol']} 涨跌 {change_pct:+.2f}%，成交量放大至 {volume:,}。")
                event = {"type": "金融风险", "title": "市场剧烈波动", "detail": f"{source['symbol']} {change_pct:+.2f}% · 控制事件", "time": now.strftime("%H:%M:%S")}
                db.commit(); self.recent_ticks.append(self._tick_dict(tick, self.tick_count))
            elif scenario == "large_order":
                source = self.order_events[self.order_cursor % len(self.order_events)]; self.order_cursor += 1
                amount = round(max(1800.0, source["amount"] * 12), 2)
                order = EcommerceOrder(order_code=f"EXERCISE-{source['source_id'][:8]}-{self.tick_count:06d}", user_id=source["user_id"], product=source["product"], category=source["category"], region=source["region"], amount=amount, is_anomaly=True)
                db.add(order)
                self._alert(db, "ecommerce", "高", "控制事件：大额异常订单", f"控制事件（非原始订单）：R${amount:,.2f}，品类 {source['category']}。")
                event = {"type": "电商风控", "title": "大额异常订单", "detail": f"R${amount:,.2f} · 控制事件", "time": now.strftime("%H:%M:%S")}
                db.commit(); payload = self._order_dict(order); payload["source_order_id"] = source["source_id"]; self.order_source_lookup[order.order_code] = {**payload, "source_time": source["source_time"]}; self.recent_orders.appendleft(payload)
            else:
                self._alert(db, "sentiment", "高", "控制事件：负面评论激增", "控制事件：中文商品评价负面比例在短窗口内显著上升，建议核验产品质量、物流和售后问题。")
                event = {"type": "舆情风险", "title": "负面评论激增", "detail": "中文商品评论负面信号 · 控制事件", "time": now.strftime("%H:%M:%S")}
                db.commit()
        self.kafka_messages += 1; self.spark_latency = 45
        self.exercise_events.appendleft(event)
        return self.snapshot()

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
                "dataset": {"mode": "真实历史数据回放", **self.datasets.metadata()},
                "exercise_events": list(self.exercise_events),
                "nodes": [{"name": "节点 1 · 主控", "status": "healthy", "role": "Web / PostgreSQL / Spark Master"}, {"name": "节点 2 · 计算 A", "status": "healthy", "role": "Kafka / Spark Worker / MinIO"}, {"name": "节点 3 · 计算 B", "status": "healthy", "role": "Kafka / Spark Worker / Redis"}],
            }

    def order_review(self, order_code: str) -> dict:
        order = self.order_source_lookup.get(order_code)
        if not order:
            raise KeyError(order_code)
        reviews = self.datasets.order_reviews(order["source_order_id"])
        return {
            "order": order,
            "reviews": reviews,
            "analysis": {
                "source": "Olist Brazilian E-Commerce Dataset · 真实订单评价",
                "summary": "该订单暂无文字评价，仅保留星级评分。" if reviews and all("未留下文字" in item["text"] for item in reviews) else "情感标签由 Olist 的 1-5 星真实评分生成：4-5 星正面、3 星中性、1-2 星负面。",
            },
        }

    def recommendations(self, user_id: str) -> dict:
        return self.datasets.recommendations_for_user(user_id)


realtime = RealtimeService()
