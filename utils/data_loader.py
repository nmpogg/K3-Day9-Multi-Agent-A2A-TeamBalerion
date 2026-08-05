"""
utils/data_loader.py
Load all Olist CSVs once at startup and expose indexed lookups.
"""
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DataStore:
    orders: Dict[str, dict] = field(default_factory=dict)
    items: Dict[str, List[dict]] = field(default_factory=dict)
    payments: Dict[str, List[dict]] = field(default_factory=dict)
    sellers: Dict[str, dict] = field(default_factory=dict)


def load_all_data(data_dir: str = "data") -> DataStore:
    """Load all required CSVs into memory once. Returns indexed DataStore."""
    base = Path(data_dir)
    store = DataStore()

    # --- Orders ---
    print("[DataLoader] Loading orders...")
    orders_df = pd.read_csv(base / "olist_orders_dataset.csv")
    for _, row in orders_df.iterrows():
        store.orders[row["order_id"]] = row.to_dict()

    # --- Order Items ---
    print("[DataLoader] Loading order items...")
    items_df = pd.read_csv(base / "olist_order_items_dataset.csv")
    for _, row in items_df.iterrows():
        oid = row["order_id"]
        store.items.setdefault(oid, []).append(row.to_dict())

    # --- Payments ---
    print("[DataLoader] Loading payments...")
    payments_df = pd.read_csv(base / "olist_order_payments_dataset.csv")
    for _, row in payments_df.iterrows():
        oid = row["order_id"]
        store.payments.setdefault(oid, []).append(row.to_dict())

    # --- Sellers ---
    print("[DataLoader] Loading sellers...")
    sellers_df = pd.read_csv(base / "olist_sellers_dataset.csv")
    for _, row in sellers_df.iterrows():
        store.sellers[row["seller_id"]] = row.to_dict()

    print(f"[DataLoader] Done. {len(store.orders)} orders, {len(store.sellers)} sellers loaded.")
    return store
