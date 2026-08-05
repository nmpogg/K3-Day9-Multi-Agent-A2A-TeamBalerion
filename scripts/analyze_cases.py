"""
scripts/analyze_cases.py - Deep analysis of all outputs vs raw data.
Detects potential misclassifications and issues.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_all_data

def main():
    store = load_all_data("data")
    in_dir = Path("input")
    out_dir = Path("output")

    issues_found = []

    for f in sorted(in_dir.glob("EC_*.json")):
        with open(f, encoding="utf-8") as fp:
            inp = json.load(fp)
        with open(out_dir / f.name, encoding="utf-8") as fp:
            out = json.load(fp)

        case_id = f.stem
        order_id = inp["customer_request"]["claimed_order_id"]
        issue = out["assessment"]["primary_issue"]
        refund = out["financial_resolution"]["recommended_refund_brl"]
        pay_total = out["financial_resolution"]["payment_total_brl"]
        freight = out["financial_resolution"]["freight_total_brl"]
        item_total = out["financial_resolution"]["item_total_brl"]

        order = store.orders.get(order_id, {})
        payments = store.payments.get(order_id, [])
        items = store.items.get(order_id, [])

        num_pays = len(payments)
        actual_pay_total = round(sum(float(p.get("payment_value", 0)) for p in payments), 2)
        actual_item_total = round(sum(float(i.get("price", 0)) for i in items), 2)
        actual_freight_total = round(sum(float(i.get("freight_value", 0)) for i in items), 2)
        expected_sum = round(actual_item_total + actual_freight_total, 2)
        diff = abs(actual_pay_total - expected_sum)

        flags = []

        # 1. Financial mismatch?
        if abs(pay_total - actual_pay_total) > 0.01:
            flags.append(f"PAY_MISMATCH: output={pay_total} vs actual={actual_pay_total}")
        if abs(item_total - actual_item_total) > 0.01:
            flags.append(f"ITEM_MISMATCH: output={item_total} vs actual={actual_item_total}")
        if abs(freight - actual_freight_total) > 0.01:
            flags.append(f"FREIGHT_MISMATCH: output={freight} vs actual={actual_freight_total}")

        # 2. unsupported_late_claim but has multiple payments? Possible split candidate
        if issue == "unsupported_late_claim" and num_pays >= 2:
            flags.append(f"POSSIBLE_SPLIT: {num_pays} payments, diff={diff:.4f}")

        # 3. valid_split_payment details
        if issue == "valid_split_payment":
            flags.append(f"split: npays={num_pays}, total={actual_pay_total}, sum={expected_sum}, diff={diff:.4f}")

        # 4. Refund check for late delivery
        if issue in ("late_delivery_seller", "late_delivery_logistics"):
            if abs(refund - actual_freight_total) > 0.01:
                flags.append(f"FREIGHT_REFUND_WRONG: refund={refund} vs freight={actual_freight_total}")

        # 5. Refund check for canceled/unavailable
        if issue in ("canceled_order_paid", "unavailable_order_paid"):
            if abs(refund - actual_pay_total) > 0.01:
                flags.append(f"FULL_REFUND_WRONG: refund={refund} vs total_pay={actual_pay_total}")

        # 6. Check evidence IDs - are all payment_ids included?
        output_payment_ids = out["affected_entities"]["payment_ids"]
        expected_pay_ids = [f"{order_id}:{int(p.get('payment_sequential',0))}" for p in payments]
        missing_pays = set(expected_pay_ids[:5]) - set(output_payment_ids)
        if missing_pays:
            flags.append(f"MISSING_PAYMENT_IDS: {missing_pays}")

        # 7. Check item_ids
        output_item_ids = out["affected_entities"]["item_ids"]
        expected_item_ids = [f"{order_id}:{int(i.get('order_item_id',0))}" for i in items[:5]]
        missing_items = set(expected_item_ids) - set(output_item_ids)
        if missing_items:
            flags.append(f"MISSING_ITEM_IDS: {missing_items}")

        if flags:
            issues_found.append((case_id, issue, flags))
            print(f"\n{case_id} [{issue}]:")
            for flag in flags:
                print(f"  -> {flag}")

    if not issues_found:
        print("No issues found! All outputs look correct.")
    else:
        print(f"\nTotal issues: {len(issues_found)} cases")

if __name__ == "__main__":
    main()
