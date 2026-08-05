"""
scripts/test_late_cases.py
Find and test orders that are late to verify late delivery rules (3 & 4).
Also tests canceled/unavailable orders.
"""
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_all_data
from agents.coordinator import process_case


def _parse_dt(s):
    if not s or str(s) in ("nan", "NaT", ""):
        return None
    try:
        return datetime.strptime(str(s)[:19], "%Y-%m-%d %H:%M:%S")
    except:
        return None


def find_test_cases(store, n=2):
    """Find one of each interesting case type."""
    cases = {
        "late_seller": None,
        "late_logistics": None,
        "canceled": None,
        "unavailable": None,
    }

    for order_id, o in store.orders.items():
        status = o.get("order_status", "")

        if cases["canceled"] is None and status == "canceled":
            pays = store.payments.get(order_id, [])
            total = sum(float(p.get("payment_value", 0)) for p in pays)
            if total > 0:
                cases["canceled"] = order_id

        if cases["unavailable"] is None and status == "unavailable":
            pays = store.payments.get(order_id, [])
            total = sum(float(p.get("payment_value", 0)) for p in pays)
            if total > 0:
                cases["unavailable"] = order_id

        delivered = _parse_dt(o.get("order_delivered_customer_date"))
        estimated = _parse_dt(o.get("order_estimated_delivery_date"))
        carrier = _parse_dt(o.get("order_delivered_carrier_date"))

        if delivered and estimated and carrier and delivered > estimated:
            items = store.items.get(order_id, [])
            for item in items:
                limit = _parse_dt(item.get("shipping_limit_date"))
                if limit and carrier > limit and cases["late_seller"] is None:
                    cases["late_seller"] = order_id
                if limit and carrier <= limit and cases["late_logistics"] is None:
                    cases["late_logistics"] = order_id

        if all(v is not None for v in cases.values()):
            break

    return cases


def run_test(order_id, label, store):
    fake_input = {
        "case_id": f"TEST_{label.upper()}",
        "opened_at": "2018-10-18T00:00:00-03:00",
        "customer_request": {
            "language": "vi",
            "message": "Test",
            "claimed_order_id": order_id
        },
        "policy_version": "EC_POLICY_V1"
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(fake_input, f)
        tmp = Path(f.name)

    output, trace = process_case(tmp, store)
    tmp.unlink()

    issue = output["assessment"]["primary_issue"]
    status = output["assessment"]["case_status"]
    refund = output["financial_resolution"]["recommended_refund_brl"]
    payment_total = output["financial_resolution"]["payment_total_brl"]
    freight = output["financial_resolution"]["freight_total_brl"]

    print(f"\n[{label}] order={order_id[:16]}...")
    print(f"  primary_issue   : {issue}")
    print(f"  case_status     : {status}")
    print(f"  payment_total   : {payment_total} BRL")
    print(f"  freight_total   : {freight} BRL")
    print(f"  refund          : {refund} BRL")
    print(f"  evidence_ids    : {output['evidence_ids']}")
    print(f"  verifier_errors : {trace['agents']['verifier_agent']['errors']}")
    return issue


def main():
    print("Loading data...")
    store = load_all_data("data")
    print("Finding test cases...")
    cases = find_test_cases(store)

    results = {}
    for label, order_id in cases.items():
        if order_id:
            results[label] = run_test(order_id, label, store)
        else:
            print(f"\n[{label}] No matching order found in dataset")

    print("\n=== SUMMARY ===")
    expected = {
        "late_seller": "late_delivery_seller",
        "late_logistics": "late_delivery_logistics",
        "canceled": "canceled_order_paid",
        "unavailable": "unavailable_order_paid",
    }
    all_pass = True
    for label, exp in expected.items():
        got = results.get(label, "NOT_FOUND")
        ok = "OK" if got == exp else "FAIL"
        if got != exp:
            all_pass = False
        print(f"  {ok} {label}: expected={exp}, got={got}")

    print(f"\n{'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")


if __name__ == "__main__":
    main()
