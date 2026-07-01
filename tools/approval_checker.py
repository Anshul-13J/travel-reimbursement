def check_approval_threshold(total: float, travel_type: str = "Domestic") -> dict:
    """
    Return the required approval level based on total claim amount and travel type.
    Thresholds from policy_rules_matrix.md section 5.
    """
    if travel_type.lower() == "domestic":
        if total <= 10_000:
            level, label = "auto", "Auto Approval"
        elif total <= 50_000:
            level, label = "manager", "Manager Approval Required"
        else:
            level, label = "director", "Director Approval Required"
    else:
        # International — thresholds approx INR equivalent
        if total <= 42_000:   # ~USD 500
            level, label = "manager", "Manager Approval Required"
        elif total <= 168_000:  # ~USD 2,000
            level, label = "director", "Director Approval Required"
        else:
            level, label = "cfo", "CFO Approval Required"

    return {
        "total": total,
        "travel_type": travel_type,
        "approval_level": level,
        "approval_label": label,
        "auto_approve": level == "auto",
    }
