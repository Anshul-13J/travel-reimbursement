# Policy Rules Matrix

This document supplements the narrative travel policy with implementation-friendly rules in Markdown form.

## 1. Submission Timeline

| Rule | Threshold | Outcome |
|---|---:|---|
| Soft late submission | > 15 days | Manager approval / manual review |
| Hard late submission | > 30 days | Reject |

## 2. Receipt Requirements

| Category | Receipt Requirement |
|---|---|
| Hotel | Always required |
| Flight | Always required |
| Meals | Required when amount > INR 500 |
| Taxi / Transport | Required when amount > INR 300 |

## 3. Category Limits

### Flights

| Travel Type | Rule | Outcome |
|---|---|---|
| Domestic | Economy only, max INR 15,000 | Above cap -> partial approve or manual review if unclear |
| International | Economy by default | Business class requires approval |

### Trains

| Class | Outcome |
|---|---|
| AC Chair Car | Allowed |
| AC 2-Tier | Allowed |
| First Class AC | Manual review / manager approval |

### Hotels

| Travel Type | Location | Limit |
|---|---|---:|
| Domestic | Tier 1 city | INR 6,000 per night |
| Domestic | Tier 2 city | INR 4,000 per night |
| International | Any | USD 150 per night |

Additional rule: luxury hotels require manual review if prior approval is not available.

### Local Transport

| Rule | Threshold | Outcome |
|---|---:|---|
| Daily transport limit | INR 1,500 | Above cap -> partial approve |
| Surge pricing justification | > 50% surge | Manual review if justification missing |

### Meals

| Travel Type | Limit |
|---|---:|
| Domestic | INR 2,000 per day |
| International | USD 50 per day |

Non-reimbursable meal components:

- Alcohol
- Beer
- Wine
- Whiskey
- Vodka
- Mojito
- Cocktail

### Internet

| Limit Type | Threshold |
|---|---:|
| Daily limit | INR 500 |

### Parking

| Limit Type | Threshold |
|---|---:|
| Daily limit | INR 300 |

## 4. Non-Reimbursable Expenses

- Alcohol
- Entertainment
- Movie tickets
- Shopping
- Personal sightseeing
- Spa services
- Traffic fines
- Personal gifts
- Family member expenses

## 5. Approval Matrix

### Domestic Travel

| Total Claim Amount | Approval Required |
|---|---|
| <= INR 10,000 | Auto approval |
| INR 10,001 to INR 50,000 | Manager approval |
| > INR 50,000 | Director approval |

### International Travel

| Total Claim Amount | Approval Required |
|---|---|
| <= USD 500 | Manager approval |
| USD 501 to USD 2,000 | Director approval |
| > USD 2,000 | CFO approval |

## 6. Manual Review Triggers

Route to manual review when any of the following apply:

- Supporting documents are missing
- Approval requirement is unclear
- Expense exceeds applicable limit by more than 20 percent
- Business class travel lacks approval
- Receipt extraction confidence is below 0.70
- Duplicate match confidence is high but not exact
- Attendee count or business purpose is required but missing
- Vendor or category classification is ambiguous

## 7. Partial Approval Rules

- Approve only eligible line items when a receipt mixes reimbursable and non-reimbursable items
- Reject alcohol or luxury components but allow the compliant remainder when policy permits separation
- Apply category cap and reject only the amount above cap when the expense is otherwise valid

## 8. Reason Codes

| Code | Meaning |
|---|---|
| APPROVED_WITHIN_LIMIT | Expense is eligible and within policy limit |
| PARTIAL_CAP_APPLIED | Expense is eligible but exceeds the policy cap |
| PARTIAL_MIXED_ELIGIBILITY | Receipt contains both eligible and non-eligible items |
| REJECT_NON_REIMBURSABLE | Expense category or item is explicitly non-reimbursable |
| REJECT_LATE_SUBMISSION | Claim was submitted beyond the hard submission deadline |
| REJECT_DUPLICATE | Duplicate claim detected |
| MANUAL_REVIEW_MISSING_INFO | More information or documentation is required |
| MANUAL_REVIEW_POLICY_EXCEPTION | Expense may be valid only with exception approval |
