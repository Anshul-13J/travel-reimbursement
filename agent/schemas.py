from pydantic import BaseModel
from typing import List

class Expense(BaseModel):
    category: str
    amount: float
    receipt_uploaded: bool

class Claim(BaseModel):
    employee_id: str
    travel_type: str
    submission_days: int
    expenses: List[Expense]

class Decision(BaseModel):
    decision: str
    approved_amount: float
    rejected_amount: float
    missing_documents: list
    policy_references: list
    confidence: float
    explanation: str