"""
bulk_pipeline.py  ─  Process 1000s of invoice files concurrently.

Usage (called from Streamlit):
    from bulk_pipeline import run_bulk

    results = run_bulk(
        files,                    # list of (filename, bytes)
        progress_cb=st.progress,  # optional callback(done, total, current_file)
        max_workers=8,
    )
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

# These imports assume the existing app structure
from app.services.analyzer import analyze
from app.services.decision_engine import decide
from app.services.executor import execute
from app.services.learning import log_case
from app.services.risk_engine import compute_risk
from scanner import scan_invoice_pages


# ─────────────────────────────────────────────────────────────
def _process_one_file(filename: str, file_bytes: bytes) -> list[dict]:
    """
    Scan image/PDF → full pipeline → return list of result dicts.
    Multi-page PDFs produce one result per page; images produce one result.
    """
    t0 = time.perf_counter()

    # STEP 1 — Vision scan: image/PDF → structured fields (one per page)
    pages = scan_invoice_pages(file_bytes, filename)

    results = []
    for scanned in pages:
        # STEP 2 — LLM analysis (root cause)
        analysis = analyze(scanned)

        # STEP 3 — Risk score
        risk = compute_risk(scanned)

        # STEP 4 — Decision
        decision = decide(analysis, risk)

        # STEP 5 — Execute action
        result = execute(decision, scanned)

        request_id = str(uuid4())
        processed_at = datetime.now(timezone.utc).isoformat()

        # STEP 6 — Audit log
        log_case(
            data=scanned,
            analysis=analysis,
            risk=risk,
            decision=decision,
            result=result,
            request_id=request_id,
            processed_at=processed_at,
        )

        total_ms = round((time.perf_counter() - t0) * 1000, 2)
        results.append({
            "filename": scanned.get("_filename", filename),
            "scanned_fields": scanned,
            "analysis": analysis,
            "risk_score": risk,
            "decision": decision,
            "result": result,
            "meta": {
                "request_id": request_id,
                "processed_at": processed_at,
                "total_ms": total_ms,
                "scan_source": scanned.get("_scan_source", "unknown"),
                "page_number": scanned.get("_page_number", 1),
                "total_pages": scanned.get("_total_pages", 1),
                "source_file": scanned.get("_source_file", filename),
            },
        })

    return results


# ─────────────────────────────────────────────────────────────
def run_bulk(
    files: list[tuple[str, bytes]],
    progress_cb: Callable | None = None,
    max_workers: int = 8,
) -> dict:
    """
    Process a list of (filename, bytes) concurrently.

    progress_cb(done: int, total: int, filename: str) is called after each file.

    Returns summary + per-file results.
    """
    total = len(files)
    errors: list[dict] = []
    done_count = 0

    # outputs now collects expanded rows (one per invoice page, not per file)
    outputs: list[dict] = []
    outputs_lock = __import__("threading").Lock()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_file = {
            pool.submit(_process_one_file, fname, fbytes): (fname, fbytes)
            for fname, fbytes in files
        }

        for future in as_completed(future_to_file):
            fname, _ = future_to_file[future]
            try:
                page_rows = future.result()
            except Exception as exc:
                page_rows = [{
                    "filename": fname,
                    "error": str(exc),
                    "decision": "error",
                    "risk_score": 0.0,
                }]
                errors.append({"filename": fname, "error": str(exc)})

            with outputs_lock:
                outputs.extend(page_rows)
                for row in page_rows:
                    if "error" in row:
                        errors.append({"filename": row["filename"], "error": row["error"]})

            done_count += 1
            if progress_cb:
                progress_cb(done_count, total, fname)

    # ── Summary stats ──────────────────────────────────────────
    valid = [o for o in outputs if "error" not in o]
    avg_risk = (
        sum(o["risk_score"] for o in valid) / len(valid) if valid else 0.0
    )
    decision_counts = {d: 0 for d in ("auto_approve", "manual_review", "auto_reject", "error")}
    for o in outputs:
        decision_counts[o.get("decision", "error")] = (
            decision_counts.get(o.get("decision", "error"), 0) + 1
        )

    root_cause_counts: dict[str, int] = {}
    for o in valid:
        rc = o["analysis"].get("root_cause", "unknown")
        root_cause_counts[rc] = root_cause_counts.get(rc, 0) + 1

    scan_sources = {}
    for o in valid:
        src = o["meta"].get("scan_source", "unknown")
        scan_sources[src] = scan_sources.get(src, 0) + 1

    return {
        "summary": {
            "total": total,
            "processed": len(valid),
            "errors": len(errors),
            **decision_counts,
            "average_risk": round(avg_risk, 3),
            "root_cause_breakdown": root_cause_counts,
            "scan_sources": scan_sources,
        },
        "items": outputs,
        "error_log": errors,
    }