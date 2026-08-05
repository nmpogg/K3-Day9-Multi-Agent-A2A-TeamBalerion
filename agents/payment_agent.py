"""
agents/payment_agent.py

Analyzes payment rows: total payment, item totals, freight totals.
Pure Python, no LLM.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from utils.data_loader import DataStore
from agents.order_seller_agent import OrderAnalysis


@dataclass
class PaymentAnalysis:
    payment_rows: List[dict] = field(default_factory=list)
    total_payment_brl: float = 0.0
    item_total_brl: float = 0.0
    freight_total_brl: float = 0.0
    payment_ids: List[str] = field(default_factory=list)  # "<order_id>:<sequential>"
    is_split: bool = False  # True if >= 2 payment rows
    is_reconciled: bool = False  # total_payment ≈ item+freight ±0.10


def analyze_payment(order_id: str, order: OrderAnalysis, store: DataStore) -> PaymentAnalysis:
    """
    Compute payment totals and reconcile against item + freight values.
    """
    payment_rows = store.payments.get(order_id, [])

    total_payment = round(sum(float(p.get("payment_value", 0.0)) for p in payment_rows), 2)
    item_total = round(sum(item.price for item in order.items), 2)
    freight_total = round(sum(item.freight_value for item in order.items), 2)

    payment_ids = [
        f"{order_id}:{int(p.get('payment_sequential', 0))}"
        for p in payment_rows
    ]

    is_split = len(payment_rows) >= 2
    # Reconciled: |total_payment - (item + freight)| <= 0.10 BRL
    expected = round(item_total + freight_total, 2)
    is_reconciled = abs(total_payment - expected) <= 0.10

    return PaymentAnalysis(
        payment_rows=payment_rows,
        total_payment_brl=total_payment,
        item_total_brl=item_total,
        freight_total_brl=freight_total,
        payment_ids=payment_ids,
        is_split=is_split,
        is_reconciled=is_reconciled,
    )
