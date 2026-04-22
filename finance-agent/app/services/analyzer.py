import json
import time

import httpx

from app.config import settings


def _rule_fallback(data, reason):
    if data["variance_amount"] > 0:
        return {
            "root_cause": "price_variance",
            "confidence": 0.8,
            "explanation": f"Fallback analysis: invoice exceeds expected by {data['variance_amount']} ({reason})",
            "source": "rules_fallback",
        }

    return {
        "root_cause": "unknown",
        "confidence": 0.5,
        "explanation": f"Fallback analysis: no clear issue detected ({reason})",
        "source": "rules_fallback",
    }


def _build_messages(data):
    return [
        {
            "role": "system",
            "content": (
                "You are a finance exception analyst. "
                "Return only valid JSON with keys: root_cause, confidence, explanation. "
                "confidence must be a float between 0 and 1."
            ),
        },
        {
            "role": "user",
            "content": (
                "Analyze this invoice mismatch event and infer the likely root cause:\n"
                f"{json.dumps(data, default=str)}"
            ),
        },
    ]


def analyze(data):
    if not settings.groq_api_key:
        return _rule_fallback(data, "missing GROQ_API_KEY")

    payload = {
        "model": settings.groq_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": _build_messages(data),
    }

    url = f"{settings.groq_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    start = time.perf_counter()
    for attempt in range(3):
        try:
            with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            result = {
                "root_cause": str(parsed.get("root_cause", "unknown")),
                "confidence": float(parsed.get("confidence", 0.5)),
                "explanation": str(parsed.get("explanation", "No explanation provided")),
                "source": "groq_llm",
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }
            result["confidence"] = max(0.0, min(result["confidence"], 1.0))
            return result
        except Exception as exc:
            if attempt == 2:
                return _rule_fallback(data, f"llm_error: {exc}")

    return _rule_fallback(data, "unknown_analyzer_error")
