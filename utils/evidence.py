"""
utils/evidence.py
Build and validate evidence IDs per EC_POLICY spec.

Valid formats:
  order:<order_id>
  item:<order_id>:<order_item_id>
  payment:<order_id>:<payment_sequential>
  seller:<seller_id>
  policy:<root_cause_code>

Max 10 evidence IDs per case.
"""
import re
from typing import List, Optional

_VALID_PATTERNS = [
    re.compile(r'^order:[a-z0-9]+$'),
    re.compile(r'^item:[a-z0-9]+:\d+$'),
    re.compile(r'^payment:[a-z0-9]+:\d+$'),
    re.compile(r'^seller:[a-z0-9]+$'),
    re.compile(r'^policy:[A-Z_]+$'),
]

VALID_ROOT_CAUSE_CODES = {
    "SELLER_HANDOFF_AFTER_LIMIT",
    "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT",
    "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED",
    "DELIVERY_WITHIN_ESTIMATE",
}


def is_valid_evidence_id(eid: str) -> bool:
    return any(p.match(eid) for p in _VALID_PATTERNS)


def build_evidence_ids(
    order_id: str,
    items,           # List[ItemInfo] dataclass objects
    payments: List[dict],  # raw dicts from DataStore
    seller_id: Optional[str],
    root_cause_code: str,
) -> List[str]:
    """Build evidence IDs list. Max 10 total. Only real IDs from data."""
    ids: List[str] = []

    # order evidence (always first)
    ids.append(f"order:{order_id}")

    # item evidence (max 5) — ItemInfo is a dataclass, use attribute access
    for item in items[:5]:
        item_id = int(item.order_item_id)
        ids.append(f"item:{order_id}:{item_id}")

    # payment evidence (fill remaining slots up to max 10 - 1 for policy)
    max_payments = max(0, 8 - len(items[:5]))
    for pay in payments[:max_payments]:
        seq = int(pay.get("payment_sequential", 0))
        ids.append(f"payment:{order_id}:{seq}")

    # seller evidence
    if seller_id:
        ids.append(f"seller:{seller_id}")

    # policy evidence (always last)
    if root_cause_code in VALID_ROOT_CAUSE_CODES:
        ids.append(f"policy:{root_cause_code}")

    # cap at 10
    return ids[:10]


def validate_evidence_ids(ids: List[str]) -> List[str]:
    """Filter to only valid formatted IDs."""
    return [eid for eid in ids if is_valid_evidence_id(eid)]
