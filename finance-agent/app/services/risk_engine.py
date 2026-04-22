def compute_risk(data):
    score = 0.0

    variance_amount = float(data.get("variance_amount", 0) or 0)
    invoice_total = float(data.get("invoice_total") or 0)
    mismatch_type = str(data.get("mismatch_type", "unknown"))
    vendor_risk_score = data.get("vendor_risk_score")
    prior_disputes = int(data.get("prior_dispute_count_90d", 0) or 0)
    is_duplicate_suspected = bool(data.get("is_duplicate_suspected", False))

    if variance_amount > 5000:
        score += 0.45
    elif variance_amount > 1000:
        score += 0.25

    if invoice_total > 0:
        variance_ratio = variance_amount / invoice_total
        if variance_ratio > 0.2:
            score += 0.2
        elif variance_ratio > 0.08:
            score += 0.1

    if mismatch_type == "duplicate" or is_duplicate_suspected:
        score += 0.35

    if vendor_risk_score is not None:
        score += min(max(float(vendor_risk_score), 0.0), 1.0) * 0.2

    if prior_disputes >= 5:
        score += 0.2
    elif prior_disputes >= 2:
        score += 0.1

    return round(min(score, 1.0), 3)
