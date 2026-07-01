from typing import Optional
from typing_extensions import TypedDict


class ClaimState(TypedDict):
    claim_id: str
    claim: dict                    # raw payload from /submit
    normalized: dict               # cleaned and enriched claim
    policy_context: list           # chunks from ChromaDB
    rule_results: dict             # deterministic tool outputs
    needs_clarification: bool
    clarification_questions: list  # [{id, question, type, expense_idx}]
    clarification_answers: dict    # {question_id: answer_string}
    decision: dict                 # final structured decision
    audit_trail: list              # step records for UI display
    error: Optional[str]
