"""Create a replay-friendly events file from the Kaggle Olist dataset.

Download and unzip https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
then run:
python ingestion/import_olist.py --source D:/datasets/olist --output data/olist_events.csv
"""
import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Unzipped Olist CSV directory")
    parser.add_argument("--output", default="data/olist_events.csv")
    args = parser.parse_args()
    source = Path(args.source)
    orders = pd.read_csv(source / "olist_orders_dataset.csv")
    customers = pd.read_csv(source / "olist_customers_dataset.csv")
    payments = pd.read_csv(source / "olist_order_payments_dataset.csv")
    items = pd.read_csv(source / "olist_order_items_dataset.csv")
    payments = payments.groupby("order_id", as_index=False)["payment_value"].sum()
    categories = items.groupby("order_id", as_index=False)["product_id"].first()
    frame = orders.merge(customers[["customer_id", "customer_unique_id", "customer_state"]], on="customer_id", how="left").merge(payments, on="order_id", how="left").merge(categories, on="order_id", how="left")
    frame = frame[frame.order_status == "delivered"].copy()
    frame["created_at"] = pd.to_datetime(frame["order_purchase_timestamp"], errors="coerce")
    result = frame[["order_id", "customer_unique_id", "product_id", "customer_state", "payment_value", "created_at"]].rename(columns={"order_id": "order_code", "customer_unique_id": "user_id", "product_id": "product", "customer_state": "region", "payment_value": "amount"}).dropna(subset=["created_at", "amount"])
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.sort_values("created_at").to_csv(destination, index=False)
    print(f"Saved {len(result)} replay events to {destination}")


if __name__ == "__main__":
    main()

