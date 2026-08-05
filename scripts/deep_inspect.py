"""
scripts/deep_inspect.py
Deep inspect các case unsupported_late_claim và bất kỳ case nào đáng ngờ.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import load_all_data


def _parse_dt(s):
    if not s or str(s) in ("nan", "NaT", ""):
        return None
    try:
        return datetime.strptime(str(s)[:19], "%Y-%m-%d %H:%M:%S")
    except:
        return None


def main():
    store = load_all_data("data")
    in_dir = Path("input")
    out_dir = Path("output")

    print("=== DEEP INSPECT: unsupported_late_claim cases ===\n")
    for f in sorted(in_dir.glob("EC_*.json")):
        with open(f, encoding="utf-8") as fp:
            inp = json.load(fp)
        with open(out_dir / f.name, encoding="utf-8") as fp:
            out = json.load(fp)

        issue = out["assessment"]["primary_issue"]
        if issue != "unsupported_late_claim":
            continue

        case_id = f.stem
        order_id = inp["customer_request"]["claimed_order_id"]
        order = store.orders.get(order_id, {})
        items = store.items.get(order_id, [])
        payments = store.payments.get(order_id, [])

        status = order.get("order_status", "?")
        delivered = _parse_dt(order.get("order_delivered_customer_date"))
        estimated = _parse_dt(order.get("order_estimated_delivery_date"))
        carrier = _parse_dt(order.get("order_delivered_carrier_date"))

        is_late = delivered is not None and estimated is not None and delivered > estimated
        num_pays = len(payments)
        total_pay = round(sum(float(p.get("payment_value", 0)) for p in payments), 2)
        item_total = round(sum(float(i.get("price", 0)) for i in items), 2)
        freight_total = round(sum(float(i.get("freight_value", 0)) for i in items), 2)
        diff = abs(total_pay - (item_total + freight_total))

        print(f"{case_id}: order_id={order_id[:16]}...")
        print(f"  status: {status}")
        print(f"  delivered: {delivered} | estimated: {estimated}")
        print(f"  carrier: {carrier}")
        print(f"  is_late: {is_late}")
        print(f"  num_payments: {num_pays} | total_pay: {total_pay} | item+freight: {item_total+freight_total:.2f} | diff: {diff:.4f}")
        
        for item in items:
            limit = _parse_dt(item.get("shipping_limit_date"))
            seller = item.get("seller_id", "?")[:16]
            print(f"  item {item.get('order_item_id')}: seller={seller}... limit={limit}")

        # Check: could this actually be valid_split_payment?
        if num_pays >= 2 and diff <= 0.10:
            print(f"  *** COULD BE valid_split_payment! diff={diff}")
        print()

    print("\n=== CONFIDENCE SCORE ANALYSIS ===")
    print("Current hardcoded confidences:")
    print("  canceled/unavailable -> 0.98")
    print("  late_delivery_seller -> 0.95")
    print("  late_delivery_logistics -> 0.93")
    print("  valid_split_payment -> 0.90")
    print("  unsupported_late_claim -> 0.85")
    print()

    # Check what 'confidence' values might be expected
    # Typically: 1.0 for cases where the rule is perfectly clear
    # Cases where delivered <= estimated → truly not late → very confident
    unsupported_cases = []
    for f in sorted(in_dir.glob("EC_*.json")):
        with open(f, encoding="utf-8") as fp:
            inp = json.load(fp)
        with open(out_dir / f.name, encoding="utf-8") as fp:
            out = json.load(fp)
        if out["assessment"]["primary_issue"] == "unsupported_late_claim":
            order_id = inp["customer_request"]["claimed_order_id"]
            order = store.orders.get(order_id, {})
            delivered = _parse_dt(order.get("order_delivered_customer_date"))
            estimated = _parse_dt(order.get("order_estimated_delivery_date"))
            if delivered and estimated:
                diff_days = (estimated - delivered).days
                print(f"{f.stem}: delivered {diff_days} days BEFORE estimate -> confident!")


if __name__ == "__main__":
    main()
