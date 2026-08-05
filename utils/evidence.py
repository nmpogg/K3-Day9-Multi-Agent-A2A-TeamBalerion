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
    """Build evidence IDs list. Max 10 total. Only real IDs from data.

    Priority order to ensure the most important evidence is always included:
      1. order:X          (always required)
      2. policy:X         (always required — must never be cut by 10-cap)
      3. seller:X         (only if seller is responsible party, passed by coordinator)
      4. payment:X:N      (payment records)
      5. item:X:N         (item records)
    """
    MAX = 10

    # GUARANTEED entries — must always be present
    guaranteed = [f"order:{order_id}"]
    if root_cause_code in VALID_ROOT_CAUSE_CODES:
        guaranteed.append(f"policy:{root_cause_code}")

    # OPTIONAL entries — fill remaining slots in priority order
    optional: List[str] = []

    # Seller evidence (only if seller is responsible — controlled by caller)
    if seller_id:
        optional.append(f"seller:{seller_id}")

    # Payment evidence — important for proving financial transactions
    for pay in payments:
        seq = int(pay.get("payment_sequential", 0))
        optional.append(f"payment:{order_id}:{seq}")

    # Item evidence
    for item in items:
        item_id = int(item.order_item_id)
        optional.append(f"item:{order_id}:{item_id}")

    # Fill up to MAX, guaranteed entries always included
    remaining = MAX - len(guaranteed)
    result = guaranteed + optional[:remaining]

    return result[:MAX]


def validate_evidence_ids(ids: List[str]) -> List[str]:
    """Filter to only valid formatted IDs."""
    return [eid for eid in ids if is_valid_evidence_id(eid)]
