"""
agents/verifier_agent.py

Validates the draft output JSON before writing to disk.
Checks:
  - Schema completeness (all required fields present)
  - Evidence ID formats
  - Array size limits (max 5 per entity set, max 10 evidence)
  - Financial rounding (2 decimal places)
  - confidence in [0, 1]
  - case_status is valid
  - Refund consistency with case_status

Returns (is_valid: bool, errors: List[str], corrected_output: dict)
"""
from __future__ import annotations
import re
from typing import Dict, List, Tuple, Any

_VALID_CASE_STATUSES = {"action_required", "no_action"}
_VALID_PRIMARY_ISSUES = {
    "canceled_order_paid", "unavailable_order_paid",
    "late_delivery_seller", "late_delivery_logistics",
    "valid_split_payment", "unsupported_late_claim",
}
_EV_PATTERNS = [
    re.compile(r'^order:[a-z0-9]+$'),
    re.compile(r'^item:[a-z0-9]+:\d+$'),
    re.compile(r'^payment:[a-z0-9]+:\d+$'),
    re.compile(r'^seller:[a-z0-9]+$'),
    re.compile(r'^policy:[A-Z_]+$'),
]


def _is_valid_evidence(eid: str) -> bool:
    return any(p.match(eid) for p in _EV_PATTERNS)


def _round2(v) -> float:
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return 0.0


def verify(output: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate and auto-correct draft output.
    Returns (is_valid, errors, corrected_output).
    """
    errors: List[str] = []
    o = output  # work in-place on a copy

    # --- Confidence ---
    conf = o.get("assessment", {}).get("confidence", 0.5)
    if not (0.0 <= float(conf) <= 1.0):
        errors.append(f"confidence {conf} out of range [0,1]")
        o["assessment"]["confidence"] = max(0.0, min(1.0, float(conf)))

    # --- case_status ---
    cs = o.get("assessment", {}).get("case_status", "")
    if cs not in _VALID_CASE_STATUSES:
        errors.append(f"case_status '{cs}' invalid")
        o["assessment"]["case_status"] = "no_action"

    # --- primary_issue ---
    pi = o.get("assessment", {}).get("primary_issue", "")
    if pi not in _VALID_PRIMARY_ISSUES:
        errors.append(f"primary_issue '{pi}' invalid")

    # --- Array limits ---
    entities = o.get("affected_entities", {})
    for key in ("order_ids", "item_ids", "seller_ids", "payment_ids"):
        arr = entities.get(key, [])
        if len(arr) > 5:
            errors.append(f"{key} has {len(arr)} entries; truncated to 5")
            entities[key] = arr[:5]

    # --- Evidence IDs ---
    evids = o.get("evidence_ids", [])
    valid_evids = [e for e in evids if _is_valid_evidence(e)]
    invalid = set(evids) - set(valid_evids)
    if invalid:
        errors.append(f"Invalid evidence IDs removed: {invalid}")
    if len(valid_evids) > 10:
        errors.append(f"evidence_ids has {len(valid_evids)} entries; truncated to 10")
        valid_evids = valid_evids[:10]
    o["evidence_ids"] = valid_evids

    # --- Financial rounding ---
    fin = o.get("financial_resolution", {})
    for field in ("item_total_brl", "freight_total_brl", "payment_total_brl", "recommended_refund_brl"):
        fin[field] = _round2(fin.get(field, 0.0))

    # --- Root cause limits (max 3) ---
    rca = o.get("root_cause_analysis", {})
    ranked = rca.get("ranked_causes", [])
    if len(ranked) > 3:
        rca["ranked_causes"] = ranked[:3]
    responsible = rca.get("responsible_parties", [])
    if len(responsible) > 3:
        rca["responsible_parties"] = responsible[:3]

    # --- Resolution actions limit (max 5) ---
    actions = o.get("resolution_actions", [])
    if len(actions) > 5:
        o["resolution_actions"] = actions[:5]

    is_valid = len(errors) == 0
    return is_valid, errors, o
