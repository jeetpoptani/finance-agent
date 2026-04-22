# ⬡ Autonomous Finance Agent
**Live Demo:** https://finance-agent-aflqftwz8ckvmjmhffdais.streamlit.app
### Invoice Intelligence Platform · v1.1.0

An AI-powered invoice exception processing system that automatically analyzes mismatched invoices, scores their risk, and makes approval decisions — without any human intervention for routine cases.

---

## What It Does

When a company receives thousands of invoices, some won't match the original Purchase Order (PO) or Goods Receipt Note (GRN) — wrong price, duplicate submission, tax error, quantity mismatch. Traditionally a finance team member manually reviews each one. This system automates that entire pipeline.

```
Invoice Mismatch Detected
        ↓
  LLM Analysis (Groq/Llama)
  → identifies root cause
        ↓
  Risk Scoring Engine
  → scores 0.0 to 1.0
        ↓
  Decision Engine
  ┌─────┴──────┐──────────┐
  ↓            ↓          ↓
Auto        Manual     Auto
Approve     Review     Reject
(risk<0.3) (0.3-0.7)  (risk≥0.7)
        ↓
  Result Executed + Logged
```

---

## Project Structure

```
TASK-3C/
├── streamlit_app.py          # Frontend UI (runs standalone)
├── finance-agent/
│   ├── app/
│   │   ├── config.py         # Environment settings
│   │   ├── main.py           # FastAPI app (optional)
│   │   ├── models/
│   │   │   └── schema.py     # Pydantic data models
│   │   ├── routes/
│   │   │   └── invoice.py    # API endpoints
│   │   └── services/
│   │       ├── analyzer.py       # LLM root cause analysis
│   │       ├── risk_engine.py    # Risk score calculator
│   │       ├── decision_engine.py# Approve/Review/Reject logic
│   │       ├── executor.py       # Executes the decision
│   │       └── learning.py       # Logs cases to JSONL
│   ├── data/
│   │   └── logs.jsonl        # Audit log (auto-created)
│   ├── .env                  # API keys (not committed)
│   └── requirements.txt
└── .vscode/
    └── settings.json
```

---

## How Each Service Works

### `analyzer.py` — LLM Root Cause Analysis
Sends the invoice mismatch data to **Groq's Llama 3.3 70B** model and asks it to identify the root cause. Returns:
- `root_cause` — e.g. `price_variance`, `duplicate_submission`
- `confidence` — float 0–1
- `explanation` — plain English reasoning

Falls back to rule-based analysis if no API key is set.

### `risk_engine.py` — Risk Scoring
Computes a risk score from 0.0 to 1.0 based on:

| Factor | Max Contribution |
|---|---|
| Variance amount > $5,000 | +0.45 |
| Variance amount $1,000–$5,000 | +0.25 |
| Variance ratio > 20% of invoice | +0.20 |
| Duplicate invoice suspected | +0.35 |
| Vendor risk score (weighted) | +0.20 |
| Prior disputes ≥ 5 in 90 days | +0.20 |

Score is capped at 1.0.

### `decision_engine.py` — Decision Logic
```
risk < 0.3   → auto_approve
risk 0.3–0.7 → manual_review
risk ≥ 0.7   → auto_reject
```

### `executor.py` — Action Execution
Executes the decision and returns a status message:
- `approved` — invoice passes through
- `pending` — routed to human reviewer
- `rejected` — vendor notified

### `learning.py` — Audit Logging
Every processed invoice is appended to `data/logs.jsonl` with full context: input data, analysis, risk score, decision, and timestamps.

---

## Frontend Pages

### Single Invoice
Fill in invoice details manually and process one invoice at a time. See the risk score, decision badge, and LLM explanation instantly.

### Batch Processing
Upload a JSON file or paste raw JSON to process hundreds of invoices at once. Get a summary breakdown and sortable results table.

### Log Viewer
Upload or point to a `logs.jsonl` file. Filter by decision type, analysis source, and minimum risk score. Export filtered results as CSV.

### Risk Simulator
Simulate risk scores locally without any API call. Adjust parameters with sliders and see a live score breakdown explaining exactly which factors are contributing.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| LLM | Groq API (Llama 3.3 70B) |
| Backend (optional) | FastAPI + Uvicorn |
| Data validation | Pydantic v2 |
| HTTP client | httpx |
| Audit logging | JSONL flat file |

---

*Built as an autonomous AI agent for finance exception management.*
