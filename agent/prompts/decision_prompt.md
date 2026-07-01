Review the following travel reimbursement claim and return a JSON decision.

Employee: {employee_id}
Travel Type: {travel_type}
Total Claimed: {total_amount}
Approval Required: {approval_label}

## Expenses

{expenses}

## Rule Check Results

{rule_results}

## Relevant Policy Context

{policy_context}

## Clarifications

{qa_section}

Important instructions:
- Evaluate each expense independently.
- If an expense is older than 365 days, reject it automatically and explain why.
- Use the indexed policy context and the expense details to decide approval, partial approval, or rejection.
- If a meal shows multiple attendees or clients, consider partial approval based on per-person eligible share.
- Water and lassi are non-alcoholic and should not be rejected as alcohol.
- If information is missing, ask for clarification rather than making a forced decision.
- Return a JSON decision object as described in your system instructions.
