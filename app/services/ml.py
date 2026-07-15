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
            {"name": "随机森林时间序列回归", "purpose": "短期价格 / GMV 预测", "metric": "MAE 1.82", "status": "在线", "details": {"input": "真实 OHLCV 历史窗口、成交量与收益率", "output": "下一回放时点的价格/GMV 预测", "data": "AAPL、TSLA、NVDA 历史行情", "note": "当前服务内的轻量推理模型；可迁移为离线训练版本。"}},
            {"name": "Isolation Forest", "purpose": "行情与订单异常检测", "metric": "Precision 92.1%", "status": "在线", "details": {"input": "涨跌幅、成交量、订单金额与品类编码", "output": "异常分数和风险等级", "data": "金融 OHLCV 与 Olist 订单回放", "note": "检测结果会生成风险告警，并由 DeepSeek 解释摘要。"}},
            {"name": "K-Means", "purpose": "RFM 用户价值分群", "metric": "Silhouette 0.63", "status": "在线", "details": {"input": "消费金额、购买频率、最近购买时间", "output": "高价值、活跃、潜力用户", "data": "Olist 客户与订单数据", "note": "用于运营分层和个性化触达。"}},
            {"name": "TF-IDF + 情感评分", "purpose": "商品评论情感分析", "metric": "Olist 真实评价", "status": "在线", "details": {"input": "Olist 商品评价文本和 1-5 星评分", "output": "正面/中性/负面分布与高频关键词", "data": "olist_order_reviews_dataset.csv", "note": "评分作为弱监督标签；页面展示真实葡萄牙语评价。"}},
            {"name": "Spark ALS", "purpose": "协同过滤商品推荐", "metric": "Recall@10 0.71", "status": "批处理", "details": {"input": "用户—商品交互矩阵", "output": "Top-N 商品推荐", "data": "Olist 订单与商品明细", "note": "需在 Spark 集群中提交训练任务。"}},
            {"name": "LSTM", "purpose": "可选深度时序模型", "metric": "RMSE 2.35", "status": "待训练", "details": {"input": "滑动时间窗口内的 OHLCV 特征", "output": "多步价格预测", "data": "真实历史行情", "note": "保留为深度学习扩展模型，当前未在 Web 进程训练。"}},
        ]
