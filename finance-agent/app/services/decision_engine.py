def decide(analysis, risk):
    if risk < 0.3:
        return "auto_approve"
    elif risk < 0.7:
        return "manual_review"
    else:
        return "auto_reject"
