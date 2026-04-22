from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from app.models.schema import BatchInvoiceRequest, InvoiceEvent, ProcessResult
from app.services.analyzer import analyze
from app.services.decision_engine import decide
from app.services.executor import execute
from app.services.learning import log_case
from app.services.risk_engine import compute_risk

router = APIRouter()


def _process_one(data):
    analysis = analyze(data)
    risk = compute_risk(data)
    decision = decide(analysis, risk)
    result = execute(decision, data)

    request_id = str(uuid4())
    processed_at = datetime.now(timezone.utc).isoformat()

    log_case(
        data=data,
        analysis=analysis,
        risk=risk,
        decision=decision,
        result=result,
        request_id=request_id,
        processed_at=processed_at,
    )

    return {
        "analysis": analysis,
        "risk_score": risk,
        "decision": decision,
        "result": result,
        "meta": {
            "request_id": request_id,
            "processed_at": processed_at,
            "analysis_source": analysis.get("source", "rules_fallback"),
        },
    }


@router.post("/process-invoice", response_model=ProcessResult)
def process_invoice(event: InvoiceEvent):
    data = event.model_dump()
    return _process_one(data)


@router.post("/process-invoices")
def process_invoices(batch: BatchInvoiceRequest):
    outputs = []
    for event in batch.invoices:
        outputs.append(_process_one(event.model_dump()))

    avg_risk = sum(item["risk_score"] for item in outputs) / len(outputs)
    summary = {
        "total": len(outputs),
        "auto_approve": sum(1 for item in outputs if item["decision"] == "auto_approve"),
        "manual_review": sum(1 for item in outputs if item["decision"] == "manual_review"),
        "auto_reject": sum(1 for item in outputs if item["decision"] == "auto_reject"),
        "average_risk": round(avg_risk, 3),
    }

    return {
        "summary": summary,
        "items": outputs,
    }
