import json
from datetime import datetime
from pathlib import Path


LOG_PATH = Path("data/logs.jsonl")


def log_case(data, analysis, risk, decision, result, request_id, processed_at):
    record = {
        "logged_at": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id,
        "processed_at": processed_at,
        "data": data,
        "analysis": analysis,
        "risk": risk,
        "decision": decision,
        "result": result,
    }

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
