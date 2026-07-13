# 真实数据目录

本目录默认不包含大型数据集，避免将课程数据直接提交到 Git。

1. 执行 `python ingestion/fetch_finance.py` 从 Yahoo Finance 下载 OHLCV 数据；
2. 从 Kaggle 下载 Olist Brazilian E-Commerce 数据集并解压；
3. 执行 `python ingestion/import_olist.py --source <解压目录>` 转换为回放事件；
4. 启动 Docker Kafka 后，执行 `python streaming/kafka_replay.py --file data/olist_events.csv --topic ecommerce-orders`；
5. 在 Spark Master 容器或服务器 1 上执行 `spark-submit --master spark://<SERVER_1>:7077 streaming/spark_job.py`。

网页自带的模拟器适合答辩演示；上述路径则用于展示“真实数据下载、清洗、Kafka 回放、Spark 聚合”的完整链路。
