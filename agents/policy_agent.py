"""
agents/policy_agent.py

Apply EC_POLICY_V1 business rules in strict priority order.
Pure Python, no LLM.

Priority order:
  1. canceled_order_paid
  2. unavailable_order_paid
  3. late_delivery_seller
  4. late_delivery_logistics
  5. valid_split_payment
  6. unsupported_late_claim  (fallback)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from agents.order_seller_agent import OrderAnalysis
from agents.payment_agent import PaymentAnalysis
from agents.delivery_agent import DeliveryAnalysis

# Mapping: primary_issue -> root_cause_code
ISSUE_TO_ROOT_CAUSE = {
    "canceled_order_paid": "ORDER_CANCELED_AFTER_PAYMENT",
    "unavailable_order_paid": "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "late_delivery_seller": "SELLER_HANDOFF_AFTER_LIMIT",
    "late_delivery_logistics": "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "valid_split_payment": "MULTIPLE_PAYMENTS_RECONCILED",
    "unsupported_late_claim": "DELIVERY_WITHIN_ESTIMATE",
}

# Mapping: primary_issue -> case_status
ISSUE_TO_STATUS = {
    "canceled_order_paid": "action_required",
    "unavailable_order_paid": "action_required",
    "late_delivery_seller": "action_required",
    "late_delivery_logistics": "action_required",
    "valid_split_payment": "no_action",
    "unsupported_late_claim": "no_action",
}

# Mapping: primary_issue -> resolution_actions
ISSUE_TO_ACTIONS = {
    "canceled_order_paid": ["issue_full_refund"],
    "unavailable_order_paid": ["issue_full_refund"],
    "late_delivery_seller": ["refund_freight"],
    "late_delivery_logistics": ["refund_freight"],
    "valid_split_payment": ["explain_valid_split_payment"],
    "unsupported_late_claim": ["reject_late_refund"],
}

# Confidence by clarity of evidence
ISSUE_TO_CONFIDENCE = {
    "canceled_order_paid": 0.98,
    "unavailable_order_paid": 0.98,
    "late_delivery_seller": 0.95,
    "late_delivery_logistics": 0.93,
    "valid_split_payment": 0.90,
    "unsupported_late_claim": 0.85,
}


@dataclass
class PolicyDecision:
    primary_issue: str
    root_cause_code: str
    case_status: str              # "action_required" | "no_action"
    confidence: float
    responsible_party_type: Optional[str]   # "seller" | "platform" | "logistics_provider" | None
    responsible_party_id: Optional[str]     # seller_id | "OLIST_PLATFORM" | "LOGISTICS_PROVIDER" | None
    recommended_refund_brl: float
    resolution_actions: List[str]


def apply_policy(
    order: OrderAnalysis,
    payment: PaymentAnalysis,
    delivery: DeliveryAnalysis,
) -> PolicyDecision:
    """
    Apply EC_POLICY_V1 rules in priority order and return a PolicyDecision.
    """
    status = order.order_status.lower()
    total_pay = payment.total_payment_brl
    freight = payment.freight_total_brl

    def _make(issue: str, party_type, party_id, refund: float) -> PolicyDecision:
        return PolicyDecision(
            primary_issue=issue,
            root_cause_code=ISSUE_TO_ROOT_CAUSE[issue],
            case_status=ISSUE_TO_STATUS[issue],
            confidence=ISSUE_TO_CONFIDENCE[issue],
            responsible_party_type=party_type,
            responsible_party_id=party_id,
            recommended_refund_brl=round(refund, 2),
            resolution_actions=ISSUE_TO_ACTIONS[issue],
        )

    # --- Rule 1: canceled ---
    if status == "canceled" and total_pay > 0:
        return _make("canceled_order_paid", "platform", "OLIST_PLATFORM", total_pay)

    # --- Rule 2: unavailable ---
    if status == "unavailable" and total_pay > 0:
        return _make("unavailable_order_paid", "platform", "OLIST_PLATFORM", total_pay)

    # --- Rule 3: late delivery, seller fault ---
    if delivery.is_late and delivery.fault == "seller":
        seller_id = delivery.responsible_seller_id or "UNKNOWN_SELLER"
        return _make("late_delivery_seller", "seller", seller_id, freight)

    # --- Rule 4: late delivery, logistics fault ---
    if delivery.is_late and delivery.fault == "logistics":
        return _make("late_delivery_logistics", "logistics_provider", "LOGISTICS_PROVIDER", freight)

    # --- Rule 5: valid split payment ---
    if payment.is_split and payment.is_reconciled:
        return _make("valid_split_payment", None, None, 0.0)

    # --- Rule 6: fallback / unsupported ---
    return _make("unsupported_late_claim", None, None, 0.0)
