VALID_DECISIONS = {"APPROVED", "PARTIAL", "REJECTED", "MANUAL_REVIEW"}


def validate_output(decision: dict) -> dict:
    """Validate the structure of a decision dict produced by the decision agent."""
    errors = []

    if decision.get("decision") not in VALID_DECISIONS:
        errors.append(
            f"Invalid decision value: {decision.get('decision')!r}. "
            f"Must be one of {sorted(VALID_DECISIONS)}"
        )

    if not isinstance(decision.get("approved_amount"), (int, float)):
        errors.append("approved_amount must be a number")

    if not isinstance(decision.get("rejected_amount"), (int, float)):
        errors.append("rejected_amount must be a number")

    if not decision.get("explanation"):
        errors.append("explanation is required")

    # Ensure optional fields exist
    decision.setdefault("policy_references", [])
    decision.setdefault("line_items", [])

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "decision": decision,
    }
