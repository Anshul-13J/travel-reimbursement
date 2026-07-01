def detect_duplicates(expenses: list) -> dict:
    """
    Detect duplicate expenses within the same claim.
    Matches on (category, date, rounded amount, vendor prefix).
    """
    seen = {}
    duplicates = []

    for idx, exp in enumerate(expenses):
        key = (
            str(exp.get("category", "")).lower().strip(),
            str(exp.get("date", "")),
            str(round(float(exp.get("amount", 0)), 2)),
            str(exp.get("vendor", "")).lower()[:20].strip(),
        )
        if key in seen:
            duplicates.append({
                "expense_idx": idx,
                "duplicate_of": seen[key],
                "type": "INTRA_CLAIM_DUPLICATE",
                "message": (
                    f"Possible duplicate of expense "
                    f"#{seen[key] + 1}"
                ),
            })
        else:
            seen[key] = idx

    return {
        "duplicates": duplicates,
        "has_duplicates": len(duplicates) > 0,
    }
