# Architecture — Multi-Agent E-commerce Dispute Resolution

## System Overview

Hệ thống gồm **6 agent** phối hợp để phân tích 50 case khiếu nại e-commerce từ dataset Olist, áp dụng `EC_POLICY_V1` và xuất kết quả chuẩn JSON.

---

## Agent Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        COORDINATOR AGENT                           │
│  Input: EC_NNN.json  ──►  orchestrate pipeline  ──►  output JSON  │
└──────┬──────────────────────────────────────────────────────┬──────┘
       │ calls sequentially                                   │ receives results
       │                                                      │
  ┌────▼──────┐  ┌──────────────┐  ┌──────────────┐         │
  │  Order &  │  │   Payment    │  │   Delivery   │         │
  │  Seller   │  │    Agent     │  │    Agent     │         │
  │  Agent    │  │              │  │              │         │
  └────┬──────┘  └──────┬───────┘  └──────┬───────┘         │
       │                │                 │                  │
       │ OrderAnalysis  │ PaymentAnalysis │ DeliveryAnalysis │
       └────────────────┴─────────────────┘                  │
                        │                                    │
                   ┌────▼──────┐                            │
                   │  Policy   │                            │
                   │   Agent   │ ──► PolicyDecision ────────┤
                   └───────────┘                            │
                                                            │
                                                   ┌────────▼──────┐
                                                   │   Verifier    │
                                                   │    Agent      │
                                                   └───────────────┘
                                                            │
                                                    Final output JSON
```

---

## Agent Roles, Permissions & Data Access

| Agent | Vai trò | Data Access | Input | Output |
|---|---|---|---|---|
| **Coordinator** | Orchestrate toàn bộ pipeline cho mỗi case | Read: input JSON | EC_NNN.json | Gọi lần lượt các agent; tổng hợp output |
| **Order & Seller Agent** | Phân tích trạng thái đơn, items, sellers, timestamps | Read: `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_sellers_dataset.csv` | order_id, DataStore | `OrderAnalysis` (status, dates, items) |
| **Payment Agent** | Đối soát payment với item + freight | Read: `olist_order_payments_dataset.csv` | order_id, OrderAnalysis, DataStore | `PaymentAnalysis` (totals, split detection) |
| **Delivery Agent** | So sánh timestamps giao hàng | Read: timestamps từ OrderAnalysis (không query CSV trực tiếp) | OrderAnalysis | `DeliveryAnalysis` (is_late, fault, seller_id) |
| **Policy Agent** | Áp dụng EC_POLICY_V1 theo thứ tự ưu tiên | Không có DB access; chỉ nhận kết quả từ các agent trên | OrderAnalysis, PaymentAnalysis, DeliveryAnalysis | `PolicyDecision` (issue, refund, action) |
| **Verifier Agent** | Validate schema, format, giới hạn | Không có DB access | Draft output dict | `(is_valid, errors, corrected_output)` |

---

## Handoff Flow

```
EC_NNN.json
    │
    ▼ [Coordinator reads case, extracts order_id]
    │
    ├──► Order & Seller Agent
    │       └─► OrderAnalysis { order_status, carrier_date, customer_date,
    │                           estimated_date, items[{item_id, seller_id,
    │                           shipping_limit_date, price, freight}] }
    │
    ├──► Payment Agent (receives OrderAnalysis for item list)
    │       └─► PaymentAnalysis { total_payment, item_total, freight_total,
    │                             payment_ids, is_split, is_reconciled }
    │
    ├──► Delivery Agent (receives OrderAnalysis for timestamps)
    │       └─► DeliveryAnalysis { is_late, fault, responsible_seller_id }
    │
    ├──► Policy Agent (receives all 3 analyses above)
    │       └─► PolicyDecision { primary_issue, root_cause_code, case_status,
    │                            confidence, responsible_party, refund_brl, actions }
    │
    ├──► Coordinator builds draft JSON (assembles all agent outputs)
    │
    └──► Verifier Agent (validates draft)
            └─► Final validated JSON  ──►  output/EC_NNN.json
                                      ──►  logging/trace.jsonl (append record)
```

---

## Business Rules (EC_POLICY_V1) — Priority Order

| Priority | primary_issue | Điều kiện | Responsible | Refund | Action |
|---|---|---|---|---|---|
| 1 | `canceled_order_paid` | status=canceled AND payment>0 | OLIST_PLATFORM | total_payment | `issue_full_refund` |
| 2 | `unavailable_order_paid` | status=unavailable AND payment>0 | OLIST_PLATFORM | total_payment | `issue_full_refund` |
| 3 | `late_delivery_seller` | late AND carrier > shipping_limit | seller_id | freight_total | `refund_freight` |
| 4 | `late_delivery_logistics` | late AND carrier <= shipping_limit | LOGISTICS_PROVIDER | freight_total | `refund_freight` |
| 5 | `valid_split_payment` | >=2 payments AND reconciled ±0.10 BRL | none | 0 | `explain_valid_split_payment` |
| 6 | `unsupported_late_claim` | fallback | none | 0 | `reject_late_refund` |

---

## File Structure

```
K3-Day9-Multi-Agent-A2A-TeamBalerion/
├── agents/
│   ├── coordinator.py          ← Orchestrator
│   ├── order_seller_agent.py   ← Order + Item analysis
│   ├── payment_agent.py        ← Payment reconciliation
│   ├── delivery_agent.py       ← Timestamp comparison
│   ├── policy_agent.py         ← Rule engine
│   └── verifier_agent.py       ← Schema validation
├── utils/
│   ├── data_loader.py          ← CSV ingestion (load once)
│   └── evidence.py             ← Evidence ID builder
├── data/                       ← Olist CSVs (9 files)
├── input/                      ← EC_001.json ... EC_050.json
├── output/                     ← EC_001.json ... EC_050.json (results)
├── logging/
│   ├── trace.jsonl             ← Audit trace (latest run)
│   └── metadata.json           ← Model & framework info
└── main.py                     ← Entry point
```

---

## Implementation Notes

- **Model**: `gpt-4o-mini` (~8B params, ≤10B limit ✓)
- **LLM usage**: Pipeline is fully deterministic (pure Python rule engine). `gpt-4o-mini` declared per spec.
- **Performance**: CSV loaded once at startup; dict-indexed for O(1) per-case lookup.
- **Timestamp handling**: All timestamps compared as Python `datetime` objects; no timezone conversion needed per spec.
- **Rounding**: All BRL amounts rounded to 2 decimal places.
- **Evidence IDs**: Only IDs directly derivable from CSV data; no hallucination.
