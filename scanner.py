"""
scanner.py — Invoice image/PDF → structured fields via Groq Vision

PDF rendering uses PyMuPDF (fitz) — pure Python, no poppler/system deps needed.
Install once:  pip install pymupdf

Key functions
─────────────
scan_invoice(file_bytes, filename) → dict
    Single-result entry point (images + single-page PDFs).

scan_invoice_pages(file_bytes, filename) → list[dict]
    Multi-result entry point for multi-page PDFs.
    Returns one result dict per page.
    For images / single-page PDFs returns a one-element list.
"""

import base64
import io
import json
import os
import time
from pathlib import Path

from groq import Groq

# ── PDF rendering via PyMuPDF (no poppler required) ───────────────────────
try:
    import fitz  # PyMuPDF — pip install pymupdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ── Groq client ────────────────────────────────────────────────────────────
_groq_client = None

GROQ_CORRECT_BASE_URL = "https://api.groq.com"

def _get_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment / .env")
        # Always pass base_url explicitly so the SDK never picks up a
        # misconfigured GROQ_BASE_URL from the environment.
        _groq_client = Groq(api_key=api_key, base_url=GROQ_CORRECT_BASE_URL)
    return _groq_client

VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",  # Current active vision model (replaces decommissioned llama-3.2 vision-preview models)
    "meta-llama/llama-4-maverick-17b-128e-instruct",  # Fallback: larger Llama 4 vision model
]

EXTRACTION_PROMPT = """You are an expert accounts-payable analyst.
Extract structured data from this invoice image and return ONLY a valid JSON object
with exactly these keys (no markdown, no explanation):

{
  "invoice_id":              "string - invoice or bill number",
  "vendor_id":               "string - vendor name or ID",
  "mismatch_type":           "one of: price_variance | quantity_variance | duplicate | tax_variance | unknown",
  "variance_amount":         "float - absolute difference between invoice total and PO/expected amount (0 if unknown)",
  "invoice_total":           "float - total amount on the invoice",
  "expected_total":          "float - PO or contract amount if visible, else same as invoice_total",
  "vendor_risk_score":       "float 0-1 - estimate vendor risk from context clues (0.5 if unknown)",
  "prior_dispute_count_90d": "int - disputes mentioned or 0",
  "is_duplicate_suspected":  "bool - true if this looks like a re-submission",
  "currency":                "string - ISO currency code e.g. USD INR EUR",
  "invoice_date":            "string - date on invoice",
  "line_items_count":        "int - number of line items visible",
  "notes":                   "string - any other observations"
}"""


# ── PDF → list of JPEG bytes via PyMuPDF ──────────────────────────────────
def _pdf_to_jpeg_bytes(file_bytes: bytes, dpi: int = 200) -> list:
    """
    Render every page of a PDF to JPEG bytes.
    Returns a list where each element is the raw JPEG bytes for that page.
    Raises RuntimeError if PyMuPDF is not installed.
    """
    if not PDF_SUPPORT:
        raise RuntimeError(
            "PyMuPDF not installed. Fix with:  pip install pymupdf\n"
            "(No poppler or other system dependency required.)"
        )
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    zoom = dpi / 72.0
    mat  = fitz.Matrix(zoom, zoom)
    result = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        result.append(pix.tobytes("jpeg"))
    doc.close()
    return result


def _jpeg_bytes_to_data_url(jpeg_bytes: bytes) -> str:
    b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def _to_data_url(file_bytes: bytes, filename: str) -> str:
    """Return a base64 data URL for any supported invoice file (page 1 for PDFs)."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        pages = _pdf_to_jpeg_bytes(file_bytes, dpi=200)
        return _jpeg_bytes_to_data_url(pages[0])
    media_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png",  ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_map.get(ext, "image/jpeg")
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{media_type};base64,{b64}"


# ── Fallback ───────────────────────────────────────────────────────────────
def _fallback(filename: str, reason: str) -> dict:
    # IMPORTANT: vendor_risk_score is set to 1.0 so compute_risk() returns >= 0.3,
    # which forces decision_engine to route to manual_review instead of auto_approve.
    # A failed scan means we have NO data — auto-approving unknown invoices is unsafe.
    return {
        "invoice_id":              Path(filename).stem,
        "vendor_id":               "UNKNOWN",
        "mismatch_type":           "unknown",
        "variance_amount":         0.0,
        "invoice_total":           0.0,
        "expected_total":          0.0,
        "vendor_risk_score":       1.0,   # Force manual_review — scan data is unknown
        "prior_dispute_count_90d": 0,
        "is_duplicate_suspected":  False,
        "currency":                "USD",
        "invoice_date":            "",
        "line_items_count":        0,
        "notes":                   f"Scan failed: {reason}",
        "_scan_source":            "fallback",
        "_filename":               filename,
    }


# ── Core vision call ───────────────────────────────────────────────────────
def _scan_data_url(data_url: str, filename: str) -> dict:
    """Send a data URL to Groq Vision. Raises RuntimeError on failure."""
    prompt_content = [
        {"type": "text",      "text": EXTRACTION_PROMPT},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]
    client = _get_client()
    last_error = None
    t0 = time.perf_counter()

    for model in VISION_MODELS:
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt_content}],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                raw = response.choices[0].message.content
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"):
                            raw = raw[4:]

                parsed = json.loads(raw) if isinstance(raw, str) else raw

                parsed["variance_amount"]         = float(parsed.get("variance_amount") or 0)
                parsed["invoice_total"]            = float(parsed.get("invoice_total")   or 0)
                parsed["expected_total"]           = float(parsed.get("expected_total")  or 0)
                parsed["vendor_risk_score"]        = float(parsed.get("vendor_risk_score") or 0.5)
                parsed["prior_dispute_count_90d"]  = int(parsed.get("prior_dispute_count_90d") or 0)
                parsed["is_duplicate_suspected"]   = bool(parsed.get("is_duplicate_suspected", False))
                parsed["line_items_count"]         = int(parsed.get("line_items_count") or 0)

                parsed["_scan_source"]     = "groq_vision"
                parsed["_scan_model"]      = model
                parsed["_scan_latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                parsed["_filename"]        = filename
                return parsed

            except Exception as exc:
                last_error = exc
                err_str = str(exc).lower()
                if "503" in str(exc) or "over capacity" in err_str or "rate" in err_str:
                    time.sleep(2 ** attempt)
                else:
                    break

    raise RuntimeError(f"all_models_failed: {last_error}")


# ── Public: single result ──────────────────────────────────────────────────
def scan_invoice(file_bytes: bytes, filename: str) -> dict:
    """Scan one invoice file → single result dict. Falls back gracefully."""
    try:
        data_url = _to_data_url(file_bytes, filename)
    except Exception as exc:
        return _fallback(filename, f"conversion_error: {exc}")
    try:
        return _scan_data_url(data_url, filename)
    except Exception as exc:
        return _fallback(filename, str(exc))


# ── Public: one result per PDF page ───────────────────────────────────────
def scan_invoice_pages(file_bytes: bytes, filename: str) -> list:
    """
    Scan every page of a PDF → list of result dicts, one per page.
    For images returns a one-element list.

    Each result includes:
        _page_number, _total_pages, _source_file
    """
    ext  = Path(filename).suffix.lower()
    stem = Path(filename).stem

    if ext != ".pdf":
        return [scan_invoice(file_bytes, filename)]

    try:
        jpeg_pages = _pdf_to_jpeg_bytes(file_bytes, dpi=200)
    except RuntimeError as exc:
        # PyMuPDF missing — surface the install instruction clearly
        return [_fallback(filename, str(exc))]
    except Exception as exc:
        return [_fallback(filename, f"pdf_render_error: {exc}")]

    total_pages = len(jpeg_pages)
    results = []

    for page_num, jpeg_bytes in enumerate(jpeg_pages, start=1):
        page_filename = f"{stem}_p{page_num}.jpg"
        try:
            data_url = _jpeg_bytes_to_data_url(jpeg_bytes)
            result   = _scan_data_url(data_url, page_filename)
        except Exception as exc:
            result = _fallback(page_filename, str(exc))

        result["_page_number"] = page_num
        result["_total_pages"] = total_pages
        result["_source_file"] = filename
        results.append(result)

    return results