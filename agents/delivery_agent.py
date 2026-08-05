"""
agents/delivery_agent.py

Compares delivery timestamps to determine:
  - Is delivery late (actual > estimated)?
  - If late, who is responsible: seller or logistics?

Per spec:
  - Seller fault: order_delivered_carrier_date > item.shipping_limit_date
  - Logistics fault: order_delivered_carrier_date <= item.shipping_limit_date (carrier received on time)

Pure Python, no LLM.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from agents.order_seller_agent import OrderAnalysis


@dataclass
class DeliveryAnalysis:
    is_late: bool
    fault: Optional[str]          # "seller" | "logistics" | None
    responsible_seller_id: Optional[str]  # only set if fault == "seller"
    # For tracing
    delivered_customer_date_str: str
    estimated_delivery_date_str: str
    delivered_carrier_date_str: str


def analyze_delivery(order: OrderAnalysis) -> DeliveryAnalysis:
    """
    Determine if delivery was late and who is responsible.
    """
    delivered = order.delivered_customer_date
    estimated = order.estimated_delivery_date
    carrier_date = order.delivered_carrier_date

    # Helpers for trace
    def _s(dt):
        return dt.isoformat() if dt else "NULL"

    # Cannot determine late if customer delivery date is missing
    if delivered is None or estimated is None:
        return DeliveryAnalysis(
            is_late=False,  # cannot confirm late
            fault=None,
            responsible_seller_id=None,
            delivered_customer_date_str=_s(delivered),
            estimated_delivery_date_str=_s(estimated),
            delivered_carrier_date_str=_s(carrier_date),
        )

    is_late = delivered > estimated

    if not is_late:
        return DeliveryAnalysis(
            is_late=False,
            fault=None,
            responsible_seller_id=None,
            delivered_customer_date_str=_s(delivered),
            estimated_delivery_date_str=_s(estimated),
            delivered_carrier_date_str=_s(carrier_date),
        )

    # Late delivery — determine fault
    # If carrier_date is unknown, default to logistics fault
    if carrier_date is None:
        return DeliveryAnalysis(
            is_late=True,
            fault="logistics",
            responsible_seller_id=None,
            delivered_customer_date_str=_s(delivered),
            estimated_delivery_date_str=_s(estimated),
            delivered_carrier_date_str=_s(carrier_date),
        )

    # Check seller fault: carrier picked up AFTER any item's shipping_limit_date
    # Per spec: "seller bị coi là bàn giao muộn nếu carrier_date > shipping_limit_date"
    for item in order.items:
        if item.shipping_limit_date is not None:
            if carrier_date > item.shipping_limit_date:
                return DeliveryAnalysis(
                    is_late=True,
                    fault="seller",
                    responsible_seller_id=item.seller_id,
                    delivered_customer_date_str=_s(delivered),
                    estimated_delivery_date_str=_s(estimated),
                    delivered_carrier_date_str=_s(carrier_date),
                )

    # Carrier received on time → logistics fault
    return DeliveryAnalysis(
        is_late=True,
        fault="logistics",
        responsible_seller_id=None,
        delivered_customer_date_str=_s(delivered),
        estimated_delivery_date_str=_s(estimated),
        delivered_carrier_date_str=_s(carrier_date),
    )
