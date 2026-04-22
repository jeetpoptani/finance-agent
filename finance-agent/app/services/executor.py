def execute(decision, data):
    if decision == "auto_approve":
        return {
            "status": "approved",
            "message": "Invoice automatically approved",
        }

    elif decision == "auto_reject":
        return {
            "status": "rejected",
            "message": "Invoice rejected and vendor notified",
        }

    else:
        return {
            "status": "pending",
            "message": "Sent for manual review",
        }
