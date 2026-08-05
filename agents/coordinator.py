"""
agents/coordinator.py

Coordinator Agent: orchestrates the full pipeline for a single case.
  1. Load input JSON
  2. Call Order & Seller Agent
  3. Call Payment Agent
  4. Call Delivery Agent
  5. Call Policy Agent
  6. Build draft output JSON
  7. Call Verifier Agent
  8. Return final output + trace record
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple

from utils.data_loader import DataStore
from utils.evidence import build_evidence_ids
from agents.order_seller_agent import analyze_order
from agents.payment_agent import analyze_payment
from agents.delivery_agent import analyze_delivery
from agents.policy_agent import apply_policy
from agents.verifier_agent import verify


def _build_draft_output(
    case: dict,
    order,
    payment,
    delivery,
    policy,
) -> Dict[str, Any]:
    """Assemble the draft output JSON from all agent results."""
    order_id = order.order_id
    case_id = case["case_id"]

    # --- Affected entities ---
    order_ids = [order_id]

    item_ids = [
        f"{order_id}:{item.order_item_id}"
        for item in order.items[:5]
    ]

    # Unique seller IDs (from policy result or all items)
    if policy.responsible_party_type == "seller" and policy.responsible_party_id:
        seller_ids = [policy.responsible_party_id]
    else:
        seen = {}
        for item in order.items:
            seen[item.seller_id] = True
        seller_ids = list(seen.keys())[:5]

    payment_ids = payment.payment_ids[:5]

    # --- Evidence IDs ---
    # For seller fault, use the responsible seller; otherwise first seller
    ev_seller_id = None
    if policy.responsible_party_type == "seller" and policy.responsible_party_id:
        ev_seller_id = policy.responsible_party_id
    elif order.items:
        ev_seller_id = order.items[0].seller_id

    evidence_ids = build_evidence_ids(
        order_id=order_id,
        items=order.items,
        payments=payment.payment_rows,
        seller_id=ev_seller_id,
        root_cause_code=policy.root_cause_code,
    )

    # --- Responsible parties ---
    responsible_parties = []
    if policy.responsible_party_type and policy.responsible_party_id:
        responsible_parties.append({
            "party_type": policy.responsible_party_type,
            "party_id": policy.responsible_party_id,
        })

    return {
        "case_id": case_id,
        "assessment": {
            "primary_issue": policy.primary_issue,
            "case_status": policy.case_status,
            "confidence": policy.confidence,
        },
        "affected_entities": {
            "order_ids": order_ids,
            "item_ids": item_ids,
            "seller_ids": seller_ids,
            "payment_ids": payment_ids,
        },
        "root_cause_analysis": {
            "ranked_causes": [
                {"cause_code": policy.root_cause_code, "rank": 1}
            ],
            "responsible_parties": responsible_parties,
        },
        "evidence_ids": evidence_ids,
        "financial_resolution": {
            "currency": "BRL",
            "item_total_brl": payment.item_total_brl,
            "freight_total_brl": payment.freight_total_brl,
            "payment_total_brl": payment.total_payment_brl,
            "recommended_refund_brl": policy.recommended_refund_brl,
        },
        "resolution_actions": policy.resolution_actions,
    }


def _build_trace_record(
    case_id: str,
    order_id: str,
    order,
    payment,
    delivery,
    policy,
    verifier_errors,
) -> Dict[str, Any]:
    """Build a JSONL trace record for audit."""
    return {
        "case_id": case_id,
        "order_id": order_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents": {
            "order_seller_agent": {
                "order_status": order.order_status,
                "delivered_carrier_date": delivery.delivered_carrier_date_str,
                "delivered_customer_date": delivery.delivered_customer_date_str,
                "estimated_delivery_date": delivery.estimated_delivery_date_str,
                "num_items": len(order.items),
                "order_found": order.found,
            },
            "payment_agent": {
                "total_payment_brl": payment.total_payment_brl,
                "item_total_brl": payment.item_total_brl,
                "freight_total_brl": payment.freight_total_brl,
                "num_payment_rows": len(payment.payment_rows),
                "is_split": payment.is_split,
                "is_reconciled": payment.is_reconciled,
            },
            "delivery_agent": {
                "is_late": delivery.is_late,
                "fault": delivery.fault,
                "responsible_seller_id": delivery.responsible_seller_id,
            },
            "policy_agent": {
                "primary_issue": policy.primary_issue,
                "root_cause_code": policy.root_cause_code,
                "case_status": policy.case_status,
                "recommended_refund_brl": policy.recommended_refund_brl,
            },
            "verifier_agent": {
                "errors": verifier_errors,
            },
        },
    }


def process_case(
    case_file: Path,
    store: DataStore,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Full pipeline for one case.
    Returns (final_output, trace_record).
    """
    with open(case_file, encoding="utf-8") as f:
        case = json.load(f)

    order_id = case["customer_request"]["claimed_order_id"]
    case_id = case["case_id"]

    # --- Agent pipeline ---
    order = analyze_order(order_id, store)
    payment = analyze_payment(order_id, order, store)
    delivery = analyze_delivery(order)
    policy = apply_policy(order, payment, delivery)

    # --- Build output ---
    draft = _build_draft_output(case, order, payment, delivery, policy)

    # --- Verify ---
    is_valid, verifier_errors, final = verify(draft)
    if verifier_errors:
        print(f"  [Verifier] {case_id}: {verifier_errors}")

    trace = _build_trace_record(case_id, order_id, order, payment, delivery, policy, verifier_errors)

    return final, trace
