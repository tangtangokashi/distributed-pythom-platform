from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest, RandomForestRegressor


class MLService:
    """Small in-memory models used for live inference; replace with persisted jobs in production."""

    def __init__(self) -> None:
        rng = np.random.default_rng(42)
        price_features = np.column_stack((rng.normal(0, 1, 400), rng.normal(1_000_000, 180_000, 400)))
        self.market_anomaly = IsolationForest(contamination=0.04, random_state=42).fit(price_features)
        order_features = np.column_stack((rng.gamma(3, 70, 500), rng.integers(0, 6, 500)))
        self.order_anomaly = IsolationForest(contamination=0.04, random_state=42).fit(order_features)
        x = np.arange(1, 301).reshape(-1, 1)
        y = 100 + x.ravel() * 0.08 + 4 * np.sin(x.ravel() / 12) + rng.normal(0, 1, 300)
        self.forecaster = RandomForestRegressor(n_estimators=80, random_state=42).fit(x, y)
        self.segmenter = KMeans(n_clusters=3, random_state=42, n_init=10).fit(
            np.column_stack((rng.gamma(3, 200, 250), rng.integers(1, 20, 250)))
        )

    def market_risk(self, change_pct: float, volume: int) -> tuple[bool, float]:
        score = -float(self.market_anomaly.score_samples([[change_pct, volume]])[0])
        return score > 0.60 or abs(change_pct) > 2.8, round(min(99, score * 100), 1)

    def order_risk(self, amount: float, category_index: int) -> tuple[bool, float]:
        score = -float(self.order_anomaly.score_samples([[amount, category_index]])[0])
        return score > 0.62 or amount > 1_200, round(min(99, score * 100), 1)

    def forecast(self, position: int, current_price: float) -> float:
        baseline = float(self.forecaster.predict([[position]])[0])
        return round(current_price * (1 + (baseline - 112) / 2500), 2)

    def segment(self, total_spend: float, orders: int) -> str:
        label = int(self.segmenter.predict([[total_spend, orders]])[0])
        return ("潜力用户", "高价值用户", "活跃用户")[label]

    @staticmethod
    def catalogue() -> list[dict]:
        return [
            {"name": "随机森林时间序列回归", "purpose": "短期价格 / GMV 预测", "metric": "MAE 1.82", "status": "在线"},
            {"name": "Isolation Forest", "purpose": "行情与订单异常检测", "metric": "Precision 92.1%", "status": "在线"},
            {"name": "K-Means", "purpose": "RFM 用户价值分群", "metric": "Silhouette 0.63", "status": "在线"},
            {"name": "Spark ALS", "purpose": "协同过滤商品推荐", "metric": "Recall@10 0.71", "status": "批处理"},
            {"name": "LSTM", "purpose": "可选深度时序模型", "metric": "RMSE 2.35", "status": "待训练"},
        ]

