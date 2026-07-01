# Per-category daily / per-trip caps (INR)
DOMESTIC_CAPS = {
    "Hotel": 6000,
    "Meals": 2000,
    "Transport": 1500,
    "Internet": 500,
    "Flight": 15000,
    "Parking": 300,
}

# International caps in INR (~approximate conversions)
INTERNATIONAL_CAPS = {
    "Meals": 4200,   # ~USD 50
    "Hotel": 12600,  # ~USD 150
    "Transport": 2000,
    "Internet": 1000,
}


def check_limits(expenses: list, travel_type: str = "Domestic") -> dict:
    caps = (
        DOMESTIC_CAPS
        if travel_type.lower() == "domestic"
        else INTERNATIONAL_CAPS
    )
    partial_approvals = []

    for idx, exp in enumerate(expenses):
        cat = str(exp.get("category", "")).strip().title()
        amount = float(exp.get("amount", 0))

        if cat in caps and amount > caps[cat]:
            cap = caps[cat]
            partial_approvals.append({
                "expense_idx": idx,
                "category": cat,
                "amount": amount,
                "cap": cap,
                "approved": cap,
                "rejected": round(amount - cap, 2),
                "message": (
                    f"{cat} exceeds policy cap of {cap:,.0f}"
                ),
            })

    return {
        "partial_approvals": partial_approvals,
        "has_caps": len(partial_approvals) > 0,
    }
