"""
scripts/test_pipeline.py
Quick smoke test to verify the full pipeline works end-to-end.
Creates a fake input file based on a real order from the dataset,
then runs the full coordinator pipeline.
"""
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_all_data
from agents.coordinator import process_case

def main():
    print("Loading data...")
    store = load_all_data("data")
    print(f"Orders: {len(store.orders)}, Items: {len(store.items)}, Payments: {len(store.payments)}, Sellers: {len(store.sellers)}")

    # Pick a real order_id from the dataset
    sample_order_id = list(store.orders.keys())[5]
    o = store.orders[sample_order_id]
    print(f"\nSample order: {sample_order_id}")
    print(f"  status: {o.get('order_status')}")
    print(f"  delivered_customer: {o.get('order_delivered_customer_date')}")
    print(f"  estimated: {o.get('order_estimated_delivery_date')}")
    print(f"  delivered_carrier: {o.get('order_delivered_carrier_date')}")

    items = store.items.get(sample_order_id, [])
    print(f"  items: {len(items)}")
    for item in items:
        print(f"    item {item.get('order_item_id')}: seller={item.get('seller_id')}, limit={item.get('shipping_limit_date')}, price={item.get('price')}, freight={item.get('freight_value')}")

    payments = store.payments.get(sample_order_id, [])
    print(f"  payments: {len(payments)}")
    for pay in payments:
        print(f"    seq={pay.get('payment_sequential')}, value={pay.get('payment_value')}")

    # Create fake input file
    fake_input = {
        "case_id": "EC_TEST",
        "opened_at": "2018-10-18T00:00:00-03:00",
        "customer_request": {
            "language": "vi",
            "message": "Test case",
            "claimed_order_id": sample_order_id
        },
        "policy_version": "EC_POLICY_V1"
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(fake_input, f)
        tmp_path = Path(f.name)

    print(f"\nRunning pipeline for {sample_order_id}...")
    output, trace = process_case(tmp_path, store)
    tmp_path.unlink()

    print("\n=== OUTPUT ===")
    print(json.dumps(output, indent=2, ensure_ascii=False))
    print("\n=== TRACE SUMMARY ===")
    for k, v in trace['agents'].items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
