# Categories that always require a receipt
ALWAYS_REQUIRED = {"Hotel", "Flight"}

# Categories requiring receipt above a threshold amount
CONDITIONAL = {
    "Meals": 500,
    "Transport": 300,
}


def validate_receipts(expenses: list) -> dict:
    issues = []

    for idx, exp in enumerate(expenses):
        cat = exp.get("category", "").strip().title()
        amount = float(exp.get("amount", 0))
        has_receipt = bool(
            exp.get("receipt_uploaded")
            or exp.get("receipt_id")
        )

        if cat in ALWAYS_REQUIRED and not has_receipt:
            issues.append({
                "expense_idx": idx,
                "type": "MISSING_RECEIPT",
                "message": f"{cat} always requires a receipt",
            })
        elif cat in CONDITIONAL and amount > CONDITIONAL[cat] and not has_receipt:
            issues.append({
                "expense_idx": idx,
                "type": "MISSING_RECEIPT",
                "message": (
                    f"{cat} receipt required when amount > "
                    f"{CONDITIONAL[cat]}"
                ),
            })

    return {"issues": issues, "valid": len(issues) == 0}
