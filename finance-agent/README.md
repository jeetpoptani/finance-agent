# Autonomous Finance Agent

A production-style MVP that ingests invoice mismatch events, uses Groq LLM for analysis, computes risk, decides next action, executes outcome, and logs cases.

## Structure

```text
finance-agent/
├── app/
│   ├── main.py
│   ├── routes/
│   │   └── invoice.py
│   ├── services/
│   │   ├── analyzer.py
│   │   ├── risk_engine.py
│   │   ├── decision_engine.py
│   │   ├── executor.py
│   │   └── learning.py
│   ├── models/
│   │   └── schema.py
├── data/
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
copy .env.example .env
```

Set `GROQ_API_KEY` in `.env`.

## Run

```bash
uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000/docs

Health checks:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/ready

## Test Payload

```json
{
  "invoice_id": "INV001",
  "vendor_id": "V001",
  "po_id": "PO001",
  "grn_id": "GRN001",
  "mismatch_type": "price_variance",
  "variance_amount": 1500,
  "currency": "USD",
  "detected_at": "2026-03-30T10:00:00",
  "invoice_total": 12000,
  "expected_total": 10500,
  "quantity_variance_pct": 12.5,
  "payment_terms_days": 45,
  "is_duplicate_suspected": false,
  "vendor_risk_score": 0.62,
  "prior_dispute_count_90d": 3,
  "invoice_count_90d": 18,
  "source_system": "sap_s4",
  "region": "NA",
  "business_unit": "industrial_procurement",
  "tags": ["high-value", "quarter-end"],
  "metadata": {
    "buyer_id": "B-1249",
    "plant_id": "PL-08"
  }
}
```

## Batch Processing

Use `POST /process-invoices` with up to 500 invoices per request.

```json
{
  "invoices": [
    {
      "invoice_id": "INV001",
      "vendor_id": "V001",
      "po_id": "PO001",
      "grn_id": "GRN001",
      "mismatch_type": "price_variance",
      "variance_amount": 1500,
      "currency": "USD",
      "detected_at": "2026-03-30T10:00:00"
    },
    {
      "invoice_id": "INV002",
      "vendor_id": "V009",
      "po_id": "PO071",
      "grn_id": "GRN071",
      "mismatch_type": "duplicate",
      "variance_amount": 200,
      "currency": "USD",
      "detected_at": "2026-03-30T11:00:00",
      "is_duplicate_suspected": true,
      "vendor_risk_score": 0.8
    }
  ]
}
```

## LLM Behavior

- Uses Groq Chat Completions API for structured JSON analysis.
- Falls back to deterministic rules if the LLM is unavailable or malformed.
- Logs source metadata (`groq_llm` or `rules_fallback`) and execution output.
- Writes append-only audit logs to `data/logs.jsonl` (JSON Lines format).
