"""
agents/order_seller_agent.py

Analyzes order status, item details, seller assignments and delivery timestamps.
All data comes from the pre-loaded DataStore (pure Python, no LLM).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from utils.data_loader import DataStore


def _parse_dt(value) -> Optional[datetime]:
    """Parse ISO-like datetime string from CSV. Returns None for NaN/empty."""
    if not value or (isinstance(value, float)):
        return None
    s = str(value).strip()
    if s in ("", "nan", "NaT"):
        return None
    # Olist timestamps: "2017-09-02 00:26:42"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


@dataclass
class ItemInfo:
    order_item_id: int
    product_id: str
    seller_id: str
    shipping_limit_date: Optional[datetime]
    price: float
    freight_value: float


@dataclass
class OrderAnalysis:
    order_id: str
    order_status: str
    delivered_carrier_date: Optional[datetime]
    delivered_customer_date: Optional[datetime]
    estimated_delivery_date: Optional[datetime]
    items: List[ItemInfo] = field(default_factory=list)
    found: bool = True  # False if order_id not in dataset


def analyze_order(order_id: str, store: DataStore) -> OrderAnalysis:
    """
    Coordinator calls this to get full order + items analysis.
    """
    order_row = store.orders.get(order_id)
    if order_row is None:
        return OrderAnalysis(
            order_id=order_id,
            order_status="unknown",
            delivered_carrier_date=None,
            delivered_customer_date=None,
            estimated_delivery_date=None,
            items=[],
            found=False,
        )

    items_raw = store.items.get(order_id, [])
    items = []
    for row in items_raw:
        items.append(ItemInfo(
            order_item_id=int(row.get("order_item_id", 0)),
            product_id=str(row.get("product_id", "")),
            seller_id=str(row.get("seller_id", "")),
            shipping_limit_date=_parse_dt(row.get("shipping_limit_date")),
            price=float(row.get("price", 0.0)),
            freight_value=float(row.get("freight_value", 0.0)),
        ))

    return OrderAnalysis(
        order_id=order_id,
        order_status=str(order_row.get("order_status", "")).strip(),
        delivered_carrier_date=_parse_dt(order_row.get("order_delivered_carrier_date")),
        delivered_customer_date=_parse_dt(order_row.get("order_delivered_customer_date")),
        estimated_delivery_date=_parse_dt(order_row.get("order_estimated_delivery_date")),
        items=items,
        found=True,
    )
