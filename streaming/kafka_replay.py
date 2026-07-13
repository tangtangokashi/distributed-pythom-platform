"""Replay a normalized CSV into Kafka; safe to run only when Kafka is available.

python streaming/kafka_replay.py --file data/olist_events.csv --topic ecommerce-orders
"""
import argparse
import csv
import json
import time

from kafka import KafkaProducer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--speed", type=float, default=5.0, help="events per second")
    args = parser.parse_args()
    producer = KafkaProducer(bootstrap_servers=args.bootstrap, value_serializer=lambda data: json.dumps(data, ensure_ascii=False).encode())
    with open(args.file, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            producer.send(args.topic, row)
            time.sleep(1 / args.speed)
    producer.flush()


if __name__ == "__main__":
    main()

