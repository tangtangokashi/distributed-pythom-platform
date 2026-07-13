"""Deploy this job to the Spark master after Kafka is available on three hosts.

spark-submit --master spark://SERVER_1:7077 streaming/spark_job.py
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, from_json, sum as spark_sum, window
from pyspark.sql.types import DoubleType, StringType, StructField, StructType, TimestampType

KAFKA = "kafka-1:9092,kafka-2:9092,kafka-3:9092"

order_schema = StructType([
    StructField("order_code", StringType()), StructField("user_id", StringType()),
    StructField("amount", DoubleType()), StructField("region", StringType()),
    StructField("created_at", TimestampType()),
])

spark = SparkSession.builder.appName("realtime-ecommerce-aggregation").getOrCreate()
raw = spark.readStream.format("kafka").option("kafka.bootstrap.servers", KAFKA).option("subscribe", "ecommerce-orders").load()
orders = raw.select(from_json(col("value").cast("string"), order_schema).alias("data")).select("data.*")
kpis = orders.withWatermark("created_at", "2 minutes").groupBy(window("created_at", "1 minute"), "region").agg(count("*").alias("orders"), spark_sum("amount").alias("gmv"))
query = kpis.selectExpr("to_json(struct(*)) AS value").writeStream.format("kafka").option("kafka.bootstrap.servers", KAFKA).option("topic", "ecommerce-kpi").option("checkpointLocation", "/tmp/checkpoints/ecommerce-kpi").outputMode("update").start()
query.awaitTermination()

